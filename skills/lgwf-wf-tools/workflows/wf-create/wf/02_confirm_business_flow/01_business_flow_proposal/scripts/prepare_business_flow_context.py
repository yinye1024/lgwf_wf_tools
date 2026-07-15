"""准备 business flow proposal 的紧凑模型上下文。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUMMARY_KEYS = (
    "workflow_id",
    "workflow_name",
    "target_package_root",
    "purpose",
    "business_goal",
    "scope",
    "non_goals",
    "target_users",
    "expected_inputs",
    "expected_outputs",
    "human_approval_points",
    "workflow_shape",
    "proposal_notes",
    "risk_notes",
    "design_rationale",
    "source_business_contract",
    "conversion_mapping",
    "prompt_workflow_context",
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def confirmed_payload(data: dict[str, Any]) -> dict[str, Any]:
    confirmed = data.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else data


def compact_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {key: data[key] for key in SUMMARY_KEYS if key in data and data[key] not in (None, "", [], {})}


def first_value(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def build_context(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    requirements = confirmed_payload(read_json(lgwf_dir / "create_requirements.json"))
    proposal = read_json(lgwf_dir / "create_requirements_proposal.json")
    source = requirements or proposal
    context = {
        "source_priority": [
            ".lgwf/create_requirements.json",
            ".lgwf/create_requirements_proposal.json",
        ],
        "current_target": {
            "workflow_id": first_value(source.get("workflow_id"), source.get("workflow_name"), source.get("name")),
            "workflow_name": first_value(source.get("workflow_name"), source.get("name")),
            "target_package_root": first_value(source.get("target_package_root"), source.get("package_root")),
        },
        "confirmed_requirements": compact_payload(requirements),
        "requirements_proposal": compact_payload(proposal),
        "creation_context_policy": {
            "target_dirs_and_files": "只读参考资料，由 TARGET_DIRS/TARGET_FILES 暴露给 Codex。",
            "must_not_execute": True,
            "usage": "只提炼业务阶段、交付、验收顺序、人工确认点、错误路径和待确认风险。",
        },
        "output_file": ".lgwf/business_flow_proposal.json",
    }
    write_json(lgwf_dir / "business_flow_proposal_context.json", context)
    return context


def main() -> None:
    context = build_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.business_flow_proposal_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
