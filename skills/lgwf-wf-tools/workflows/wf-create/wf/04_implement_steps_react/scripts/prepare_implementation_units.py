"""把实现阶段拆成可由 FOREACH 独立处理的 implementation units。"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def confirmed_payload(data: dict[str, Any]) -> dict[str, Any]:
    confirmed = data.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else data


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def slugify(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    return cleaned or fallback


def normalize_package_path(raw_path: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    if cleaned.startswith("docs/steps/"):
        cleaned = f"wf/{cleaned}"
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ":" in cleaned:
        raise ValueError(f"非法 package 相对路径: {raw_path}")
    if any(part in {"..", ".lgwf"} for part in path.parts):
        raise ValueError(f"非法 package 相对路径: {raw_path}")
    return path.as_posix().strip("/")


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def target_file(target_abs: Path, relative: str) -> str:
    return str((target_abs / normalize_package_path(relative)).resolve())


def target_dir(target_abs: Path, relative: str) -> str:
    return str((target_abs / normalize_package_path(relative)).resolve())


def source_stage_ids(step_designs: dict[str, Any]) -> list[str]:
    confirmed = confirmed_payload(step_designs)
    result: list[str] = []
    for item in as_dict_list(confirmed.get("source_business_flow_stages", [])):
        stage_id = str(item.get("stage_id", "")).strip()
        if stage_id:
            result.append(slugify(stage_id, f"stage_{len(result) + 1:02d}"))
    if result:
        return unique(result)
    for item in as_dict_list(confirmed.get("step_designs", [])):
        stage_id = str(item.get("stage_id") or item.get("stage") or "").strip()
        if stage_id:
            result.append(slugify(stage_id, f"stage_{len(result) + 1:02d}"))
    return unique(result)


def step_design_items(step_designs: dict[str, Any]) -> list[dict[str, Any]]:
    confirmed = confirmed_payload(step_designs)
    for key in ("step_designs", "step_designs_proposal"):
        items = as_dict_list(confirmed.get(key, []))
        if items:
            return items
    return []


def step_doc_paths(items: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for item in items:
        raw_path = str(item.get("doc_path") or item.get("path") or "").strip()
        if raw_path:
            result.append(normalize_package_path(raw_path))
    return unique(result)


def stage_step_designs(items: list[dict[str, Any]], stage_id: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in items:
        item_stage = str(item.get("stage_id") or item.get("stage") or "").strip()
        if item_stage and slugify(item_stage, item_stage) == stage_id:
            selected.append(item)
    return selected


def unit_payload(
    *,
    unit_id: str,
    unit_type: str,
    objective: str,
    target_abs: Path,
    package_relative_files: list[str],
    package_relative_dirs: list[str],
    implementation_context: dict[str, Any],
    implementation_reason: str,
    observe: dict[str, Any],
    step_designs: list[dict[str, Any]],
    repair_focus: list[str],
) -> dict[str, Any]:
    package_relative_files = unique([normalize_package_path(path) for path in package_relative_files])
    package_relative_dirs = unique([normalize_package_path(path) for path in package_relative_dirs])
    return {
        "unit_id": unit_id,
        "unit_type": unit_type,
        "objective": objective,
        "target_package_root": implementation_context.get("target_package_root", ""),
        "target_package_abs": implementation_context.get("target_package_abs", ""),
        "workspace_root": implementation_context.get("workspace_root", ""),
        "package_relative_files": package_relative_files,
        "package_relative_dirs": package_relative_dirs,
        "target_files": [target_file(target_abs, path) for path in package_relative_files],
        "target_dirs": [target_dir(target_abs, path) for path in package_relative_dirs],
        "implementation_reason": implementation_reason,
        "observe": observe,
        "repair_focus": repair_focus,
        "step_designs": step_designs,
    }


def all_units(
    implementation_context: dict[str, Any],
    step_designs_payload: dict[str, Any],
    implementation_reason: str,
    observe: dict[str, Any],
    repair_focus: list[str],
) -> list[dict[str, Any]]:
    target_abs = Path(str(implementation_context.get("target_package_abs", ""))).resolve()
    items = step_design_items(step_designs_payload)
    docs = step_doc_paths(items)
    units: list[dict[str, Any]] = [
        unit_payload(
            unit_id="package_contracts",
            unit_type="package",
            objective="生成或修复目标 package 入口文档、入口契约和 artifact contract。",
            target_abs=target_abs,
            package_relative_files=["AGENTS.md", "README.md", "entry_contract.json", "wf/artifact_contracts.json"],
            package_relative_dirs=[".", "wf"],
            implementation_context=implementation_context,
            implementation_reason=implementation_reason,
            observe=observe,
            step_designs=[],
            repair_focus=repair_focus,
        ),
        unit_payload(
            unit_id="root_workflow",
            unit_type="root_workflow",
            objective="生成或修复根 wf/workflow.lgwf，并复制已确认步骤设计文档到 wf/docs/steps/。",
            target_abs=target_abs,
            package_relative_files=["wf/workflow.lgwf", *docs],
            package_relative_dirs=["wf", "wf/docs", "wf/docs/steps"],
            implementation_context=implementation_context,
            implementation_reason=implementation_reason,
            observe=observe,
            step_designs=items,
            repair_focus=repair_focus,
        ),
    ]
    for index, stage_id in enumerate(source_stage_ids(step_designs_payload), start=1):
        normalized_stage = slugify(stage_id, f"stage_{index:02d}")
        units.append(
            unit_payload(
                unit_id=f"stage_{normalized_stage}",
                unit_type="stage",
                objective=f"生成或修复阶段 `{normalized_stage}` 的自包含 workflow、prompt、script 和 resource。",
                target_abs=target_abs,
                package_relative_files=[
                    f"wf/{normalized_stage}/workflow.lgwf",
                    f"wf/{normalized_stage}/agents/prompt.md",
                    f"wf/{normalized_stage}/scripts/run.py",
                    f"wf/{normalized_stage}/resources/README.md",
                ],
                package_relative_dirs=[
                    f"wf/{normalized_stage}",
                    f"wf/{normalized_stage}/agents",
                    f"wf/{normalized_stage}/scripts",
                    f"wf/{normalized_stage}/resources",
                ],
                implementation_context=implementation_context,
                implementation_reason=implementation_reason,
                observe=observe,
                step_designs=stage_step_designs(items, normalized_stage),
                repair_focus=repair_focus,
            )
        )
    units.append(
        unit_payload(
            unit_id="shared_helpers_tests",
            unit_type="support",
            objective="生成或修复共享 helper、最小测试和验证辅助文件。",
            target_abs=target_abs,
            package_relative_files=[
                "tests/README.md",
                "tests/test_workflow_structure.py",
                "wf/shared/scripts/README.md",
            ],
            package_relative_dirs=["tests", "wf/shared", "wf/shared/scripts"],
            implementation_context=implementation_context,
            implementation_reason=implementation_reason,
            observe=observe,
            step_designs=[],
            repair_focus=repair_focus,
        )
    )
    return units


def failure_texts(observe: dict[str, Any]) -> list[str]:
    failures = observe.get("failures", [])
    if isinstance(failures, list):
        return [str(item) for item in failures if str(item).strip()]
    if isinstance(failures, str) and failures.strip():
        return [failures]
    return []


def is_initial_observe(observe: dict[str, Any], failures: list[str]) -> bool:
    if observe.get("initial") is True:
        return True
    return any("首轮尚未执行" in failure for failure in failures)


def selected_unit_ids(units: list[dict[str, Any]], failures: list[str]) -> set[str]:
    combined = "\n".join(failures).replace("\\", "/")
    selected: set[str] = set()
    for unit in units:
        unit_id = str(unit.get("unit_id", ""))
        if unit_id and unit_id in combined:
            selected.add(unit_id)
            continue
        if unit_id.startswith("stage_"):
            stage_id = unit_id.removeprefix("stage_")
            if stage_id and stage_id in combined:
                selected.add(unit_id)
    package_markers = ("AGENTS.md", "README.md", "entry_contract.json", "artifact_contracts.json")
    if any(marker in combined for marker in package_markers):
        selected.add("package_contracts")
    if "wf/workflow.lgwf" in combined or "root workflow" in combined or "根" in combined:
        selected.add("root_workflow")
    if "docs/steps" in combined or "wf/docs/steps" in combined:
        selected.add("root_workflow")
    if "tests" in combined or "shared" in combined:
        selected.add("shared_helpers_tests")
    if not selected:
        selected.add("root_workflow")
        selected.update(str(unit.get("unit_id", "")) for unit in units if str(unit.get("unit_id", "")).startswith("stage_"))
    return {unit_id for unit_id in selected if unit_id}


def build_implementation_units(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    implementation_context = load_json(lgwf_dir / "implementation_context.json")
    step_designs_payload = load_json(lgwf_dir / "step_designs.json")
    implementation_reason = read_text(lgwf_dir / "implementation_reason.md")
    observe = load_json(lgwf_dir / "implementation_observe.json")
    failures = failure_texts(observe)
    units = all_units(
        implementation_context,
        step_designs_payload,
        implementation_reason,
        observe,
        failures,
    )
    if observe.get("passed") is True:
        selected = []
        selection_mode = "noop"
    elif not failures or is_initial_observe(observe, failures):
        selected = units
        selection_mode = "full"
    else:
        wanted = selected_unit_ids(units, failures)
        selected = [unit for unit in units if str(unit.get("unit_id", "")) in wanted]
        selection_mode = "repair"
    result = {
        "selection_mode": selection_mode,
        "unit_count": len(selected),
        "implementation_units": selected,
        "all_unit_ids": [str(unit.get("unit_id", "")) for unit in units],
        "failure_count": len(failures),
        "failures": failures,
    }
    write_json(lgwf_dir / "implementation_units.json", result)
    return result


def main() -> None:
    result = build_implementation_units(Path.cwd())
    print(
        json.dumps(
            {
                "lgwf_wf_create.prepare_implementation_units_result": result,
                "lgwf_wf_create.implementation_units": result["implementation_units"],
                "lgwf_wf_create.implementation_unit_results": {"items": []},
                "foreach.implement_each_unit.report": None,
                "foreach.implement_each_unit.status": None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
