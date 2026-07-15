"""生成步骤设计节点使用的动态校验契约。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REQUIRED_IMPLEMENTATION_FILE_DESIGNS = (
    "AGENTS.md",
    "README.md",
    "entry_contract.json",
    "wf/workflow.lgwf",
    "wf/artifact_contracts.json",
)


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip().replace("\\", "/") for item in value if str(item).strip()]


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def pick_identity(*sources: dict[str, Any], key: str) -> str:
    for source in sources:
        value = text(source.get(key))
        if value:
            return value
    return ""


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip().replace("\\", "/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def build_business_stage_index(stages: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    stage_ids: list[str] = []
    workflow_to_stage: dict[str, str] = {}
    for item in stages:
        stage_id = text(item.get("stage_id"))
        if stage_id:
            stage_ids.append(stage_id)
        workflow_ref = text(item.get("workflow_ref")).replace("\\", "/")
        if workflow_ref and stage_id:
            workflow_to_stage[workflow_ref] = stage_id
    return dedupe(stage_ids), workflow_to_stage


def infer_workflow_ref(stage_dir: str, stage_id: str) -> str:
    ref_dir = stage_dir or stage_id
    return f"wf/{ref_dir}/workflow.lgwf" if ref_dir else ""


def infer_stage_artifact_contract_ref(workflow_ref: str) -> str:
    if not workflow_ref.endswith("/workflow.lgwf"):
        return ""
    return f"{workflow_ref.removesuffix('/workflow.lgwf')}/artifact_contracts.json"


def strip_numeric_prefix(value: str) -> str:
    return re.sub(r"^\d+[_-]+", "", value.strip()).strip("_-")


def find_stage_contract(by_workflow: dict[str, dict[str, Any]], stage_id: str) -> dict[str, Any] | None:
    if not stage_id:
        return None
    for item in by_workflow.values():
        aliases = [str(alias).strip() for alias in item.get("aliases", []) if str(alias).strip()]
        if stage_id == text(item.get("stage_id")) or stage_id in aliases:
            return item
    return None


def build_stage_contracts(
    business_stages: list[dict[str, Any]],
    scaffold_stage_manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    business_stage_ids, workflow_to_stage = build_business_stage_index(business_stages)
    by_workflow: dict[str, dict[str, Any]] = {}

    for item in scaffold_stage_manifest:
        scaffold_stage_id = text(item.get("stage_id"))
        stage_dir = text(item.get("stage_dir")) or scaffold_stage_id
        workflow_ref = text(item.get("workflow_ref")).replace("\\", "/") or infer_workflow_ref(stage_dir, scaffold_stage_id)
        stage_dir_alias = strip_numeric_prefix(stage_dir)
        canonical_stage_id = workflow_to_stage.get(workflow_ref) or (
            stage_dir_alias if stage_dir_alias in business_stage_ids else stage_dir if stage_dir in business_stage_ids else scaffold_stage_id
        )
        if not canonical_stage_id:
            canonical_stage_id = stage_dir or workflow_ref.removeprefix("wf/").removesuffix("/workflow.lgwf")
        aliases = dedupe(
            [
                scaffold_stage_id,
                stage_dir,
                stage_dir_alias,
                *string_list(item.get("stage_aliases")),
            ]
        )
        aliases = [alias for alias in aliases if alias != canonical_stage_id]
        by_workflow[workflow_ref] = {
            "stage_id": canonical_stage_id,
            "aliases": aliases,
            "stage_dir": stage_dir,
            "workflow_ref": workflow_ref,
            "artifact_contract_ref": infer_stage_artifact_contract_ref(workflow_ref),
            "source": "scaffold_stage_manifest",
        }

    for item in business_stages:
        stage_id = text(item.get("stage_id"))
        if not stage_id:
            continue
        workflow_ref = text(item.get("workflow_ref")).replace("\\", "/")
        existing = by_workflow.get(workflow_ref) if workflow_ref else None
        if not existing:
            existing = find_stage_contract(by_workflow, stage_id)
        if existing:
            existing["stage_id"] = stage_id
            existing["aliases"] = [alias for alias in existing.get("aliases", []) if alias != stage_id]
            if workflow_ref and workflow_ref != existing.get("workflow_ref"):
                existing["workflow_aliases"] = dedupe([*string_list(existing.get("workflow_aliases")), workflow_ref])
            existing["source"] = "business_flow_and_scaffold"
            continue
        workflow_ref = workflow_ref or infer_workflow_ref(stage_id, stage_id)
        by_workflow[workflow_ref] = {
            "stage_id": stage_id,
            "aliases": [],
            "stage_dir": stage_id,
            "workflow_ref": workflow_ref,
            "artifact_contract_ref": infer_stage_artifact_contract_ref(workflow_ref),
            "source": "business_flow",
        }

    return list(by_workflow.values())


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    business_flow = load_json_object(lgwf_dir / "business_flow.json")
    requirements = load_json_object(lgwf_dir / "create_requirements.json")
    scaffold = load_json_object(lgwf_dir / "scaffold_package_result.json")
    confirmed_business_flow = nested_dict(business_flow, "confirmed") or business_flow
    scaffold_plan = nested_dict(scaffold, "scaffold_plan") or scaffold

    stage_contracts = build_stage_contracts(
        dict_list(confirmed_business_flow.get("stages", [])),
        dict_list(scaffold_plan.get("stage_manifest", [])),
    )
    canonical_stage_ids = dedupe([text(item.get("stage_id")) for item in stage_contracts])
    stage_aliases: dict[str, str] = {}
    for item in stage_contracts:
        canonical = text(item.get("stage_id"))
        for alias in item.get("aliases", []):
            if isinstance(alias, str) and alias.strip() and alias != canonical:
                stage_aliases[alias] = canonical

    scaffold_files = string_list(scaffold_plan.get("create_files"))
    required_file_designs = dedupe(
        [
            *REQUIRED_IMPLEMENTATION_FILE_DESIGNS,
            *[text(item.get("workflow_ref")) for item in stage_contracts],
            *[text(item.get("artifact_contract_ref")) for item in stage_contracts],
        ]
    )
    contract = {
        "contract_version": 1,
        "identity": {
            "workflow_id": pick_identity(requirements, confirmed_business_flow, scaffold_plan, key="workflow_id"),
            "workflow_name": pick_identity(requirements, confirmed_business_flow, scaffold_plan, key="workflow_name"),
            "target_package_root": pick_identity(requirements, scaffold_plan, confirmed_business_flow, key="target_package_root"),
            "package_profile": pick_identity(requirements, scaffold_plan, confirmed_business_flow, key="package_profile"),
        },
        "stage_identity": {
            "canonical_stage_ids": canonical_stage_ids,
            "allowed_stage_ids": dedupe([*canonical_stage_ids, *stage_aliases.keys()]),
            "stage_aliases": stage_aliases,
        },
        "required_stage_workflows": stage_contracts,
        "required_file_designs": required_file_designs,
        "scaffold_create_files": scaffold_files,
        "shape_contract": {
            "proposal_schema_ref": "resources/step_designs_proposal.schema.json",
            "passing_example_ref": "resources/step_designs_passing_example.json",
            "forbidden_source_fields": ["content", "full_source", "source_code", "code", "body"],
            "required_out_of_scope_terms": ["lgwf-wf-prompt-fix", "lgwf-wf-tools", "自动修复", "端到端运行保证"],
            "path_rule": "package-relative safe paths only; runtime_artifacts may point to .lgwf, target files and dirs may not",
        },
    }
    output_path = lgwf_dir / "step_design_validation_contract.json"
    write_json(output_path, contract)
    print(
        json.dumps(
            {"lgwf_wf_create.step_design_validation_contract": contract},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
