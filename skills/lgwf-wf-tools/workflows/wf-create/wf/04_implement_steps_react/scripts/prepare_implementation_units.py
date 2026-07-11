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


def load_scaffold_plan(root: Path) -> dict[str, Any]:
    payload = load_json(root / ".lgwf" / "scaffold_package_result.json")
    plan = payload.get("scaffold_plan", payload)
    return plan if isinstance(plan, dict) else {}


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


def strip_numeric_prefix(value: str) -> str:
    return re.sub(r"^\d+[_-]+", "", value.strip()).strip("_-")


def numbered_stage_dir(index: int, stage_id: str) -> str:
    suffix = strip_numeric_prefix(stage_id) or f"stage_{index:02d}"
    return f"{index:02d}_{suffix}"


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


def plan_string_list(plan: dict[str, Any], key: str) -> list[str]:
    value = plan.get(key, [])
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(normalize_package_path(item))
    return unique(result)


def stage_dir_from_workflow_ref(raw_path: str) -> str:
    path = PurePosixPath(normalize_package_path(raw_path))
    parts = path.parts
    if len(parts) == 3 and parts[0] == "wf" and parts[2] == "workflow.lgwf":
        stage_dir = parts[1]
        if stage_dir not in {"docs", "shared"}:
            return stage_dir
    return ""


def stage_manifest_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return as_dict_list(plan.get("stage_manifest", []))


def stage_dirs_from_plan(plan: dict[str, Any], fallback_stage_ids: list[str]) -> list[str]:
    result = [
        normalize_package_path(f"wf/{item['stage_dir']}").split("/", 1)[1]
        for item in stage_manifest_items(plan)
        if isinstance(item.get("stage_dir"), str) and str(item.get("stage_dir")).strip()
    ]
    for rel_path in plan_string_list(plan, "create_files"):
        stage_dir = stage_dir_from_workflow_ref(rel_path)
        if stage_dir:
            result.append(stage_dir)
    if result:
        return unique(result)
    return unique([slugify(stage_id, f"stage_{index:02d}") for index, stage_id in enumerate(fallback_stage_ids, start=1)])


def stage_manifest_entry(plan: dict[str, Any], stage_dir: str, index: int) -> dict[str, Any]:
    for item in stage_manifest_items(plan):
        if str(item.get("stage_dir", "")).strip() == stage_dir:
            return item
    logical_stage_id = strip_numeric_prefix(stage_dir) or f"stage_{index:02d}"
    return {
        "stage_id": slugify(logical_stage_id, f"stage_{index:02d}"),
        "stage_dir": stage_dir,
        "workflow_ref": f"wf/{stage_dir}/workflow.lgwf",
    }


def stage_planned_files(plan: dict[str, Any], stage_dir: str) -> list[str]:
    prefix = f"wf/{stage_dir}/"
    files = [path for path in plan_string_list(plan, "create_files") if path.startswith(prefix)]
    return files or [
        f"wf/{stage_dir}/workflow.lgwf",
        f"wf/{stage_dir}/agents/prompt.md",
        f"wf/{stage_dir}/scripts/run.py",
        f"wf/{stage_dir}/resources/README.md",
    ]


def stage_planned_dirs(plan: dict[str, Any], stage_dir: str) -> list[str]:
    prefix = f"wf/{stage_dir}/"
    dirs = [path for path in plan_string_list(plan, "create_dirs") if path == f"wf/{stage_dir}" or path.startswith(prefix)]
    return dirs or [
        f"wf/{stage_dir}",
        f"wf/{stage_dir}/agents",
        f"wf/{stage_dir}/scripts",
        f"wf/{stage_dir}/resources",
    ]


def package_contract_files(plan: dict[str, Any]) -> list[str]:
    files = [
        path
        for path in plan_string_list(plan, "create_files")
        if ("/" not in path and not path.startswith("tests")) or path == "wf/artifact_contracts.json"
    ]
    return files or ["AGENTS.md", "README.md", "entry_contract.json", "wf/artifact_contracts.json"]


def support_files(plan: dict[str, Any]) -> list[str]:
    files = [
        path
        for path in plan_string_list(plan, "create_files")
        if path.startswith("tests/") or path.startswith("wf/shared/")
    ]
    return files or ["tests/README.md", "tests/test_workflow_structure.py"]


def support_dirs(plan: dict[str, Any]) -> list[str]:
    dirs = [
        path
        for path in plan_string_list(plan, "create_dirs")
        if path == "tests" or path.startswith("tests/") or path.startswith("wf/shared")
    ]
    return dirs or ["tests", "wf/shared", "wf/shared/scripts"]


def stage_step_designs(items: list[dict[str, Any]], stage_id: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    expected = {slugify(stage_id, stage_id), slugify(strip_numeric_prefix(stage_id), strip_numeric_prefix(stage_id) or stage_id)}
    for item in items:
        item_stage = str(item.get("stage_id") or item.get("stage") or "").strip()
        item_values = {
            slugify(item_stage, item_stage),
            slugify(strip_numeric_prefix(item_stage), strip_numeric_prefix(item_stage) or item_stage),
        }
        if item_stage and expected.intersection(item_values):
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
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package_relative_files = unique([normalize_package_path(path) for path in package_relative_files])
    package_relative_dirs = unique([normalize_package_path(path) for path in package_relative_dirs])
    payload = {
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
    if extra:
        payload.update(extra)
    return payload


def all_units(
    implementation_context: dict[str, Any],
    step_designs_payload: dict[str, Any],
    scaffold_plan: dict[str, Any],
    implementation_reason: str,
    observe: dict[str, Any],
    repair_focus: list[str],
) -> list[dict[str, Any]]:
    target_abs = Path(str(implementation_context.get("target_package_abs", ""))).resolve()
    items = step_design_items(step_designs_payload)
    docs = step_doc_paths(items)
    fallback_stage_ids = source_stage_ids(step_designs_payload)
    stage_dirs = stage_dirs_from_plan(scaffold_plan, fallback_stage_ids)
    create_dirs = plan_string_list(scaffold_plan, "create_dirs")
    units: list[dict[str, Any]] = [
        unit_payload(
            unit_id="package_contracts",
            unit_type="package",
            objective="生成或修复目标 package 入口文档、入口契约和 artifact contract。",
            target_abs=target_abs,
            package_relative_files=package_contract_files(scaffold_plan),
            package_relative_dirs=unique([".", "wf", *[path for path in create_dirs if path in {"scripts", "ws"}]]),
            implementation_context=implementation_context,
            implementation_reason=implementation_reason,
            observe=observe,
            step_designs=[],
            repair_focus=repair_focus,
            extra={
                "scaffold_plan": scaffold_plan,
                "package_profile": scaffold_plan.get("package_profile", implementation_context.get("package_profile", "")),
                "planned_files": package_contract_files(scaffold_plan),
                "planned_dirs": unique([".", "wf", *[path for path in create_dirs if path in {"scripts", "ws"}]]),
            },
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
            extra={
                "scaffold_plan": scaffold_plan,
                "stage_manifest": stage_manifest_items(scaffold_plan),
                "planned_files": ["wf/workflow.lgwf", *docs],
                "planned_dirs": ["wf", "wf/docs", "wf/docs/steps"],
            },
        ),
    ]
    for index, stage_dir in enumerate(stage_dirs, start=1):
        manifest = stage_manifest_entry(scaffold_plan, stage_dir, index)
        stage_id = slugify(str(manifest.get("stage_id", "")).strip(), strip_numeric_prefix(stage_dir) or f"stage_{index:02d}")
        planned_files = stage_planned_files(scaffold_plan, stage_dir)
        planned_dirs = stage_planned_dirs(scaffold_plan, stage_dir)
        workflow_ref = str(manifest.get("workflow_ref") or f"wf/{stage_dir}/workflow.lgwf")
        units.append(
            unit_payload(
                unit_id=f"stage_{stage_dir}",
                unit_type="stage",
                objective=f"生成或修复阶段 `{stage_dir}` 的自包含 workflow、prompt、script 和 resource。",
                target_abs=target_abs,
                package_relative_files=planned_files,
                package_relative_dirs=planned_dirs,
                implementation_context=implementation_context,
                implementation_reason=implementation_reason,
                observe=observe,
                step_designs=stage_step_designs(items, stage_id),
                repair_focus=repair_focus,
                extra={
                    "scaffold_plan": scaffold_plan,
                    "stage_id": stage_id,
                    "stage_dir": stage_dir,
                    "workflow_ref": workflow_ref,
                    "planned_files": planned_files,
                    "planned_dirs": planned_dirs,
                },
            )
        )
    units.append(
        unit_payload(
            unit_id="shared_helpers_tests",
            unit_type="support",
            objective="生成或修复共享 helper、最小测试和验证辅助文件。",
            target_abs=target_abs,
            package_relative_files=support_files(scaffold_plan),
            package_relative_dirs=support_dirs(scaffold_plan),
            implementation_context=implementation_context,
            implementation_reason=implementation_reason,
            observe=observe,
            step_designs=[],
            repair_focus=repair_focus,
            extra={
                "scaffold_plan": scaffold_plan,
                "planned_files": support_files(scaffold_plan),
                "planned_dirs": support_dirs(scaffold_plan),
            },
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
        markers = [
            unit_id,
            str(unit.get("stage_id", "")),
            str(unit.get("stage_dir", "")),
            str(unit.get("workflow_ref", "")),
            *[str(path) for path in unit.get("planned_files", []) if isinstance(unit.get("planned_files", []), list)],
            *[str(path) for path in unit.get("planned_dirs", []) if isinstance(unit.get("planned_dirs", []), list)],
        ]
        for marker in markers:
            if marker and marker.replace("\\", "/") in combined:
                selected.add(unit_id)
                break
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
    scaffold_plan = load_scaffold_plan(root)
    implementation_reason = read_text(lgwf_dir / "implementation_reason.md")
    observe = load_json(lgwf_dir / "implementation_observe.json")
    failures = failure_texts(observe)
    units = all_units(
        implementation_context,
        step_designs_payload,
        scaffold_plan,
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
        "scaffold_plan_used": bool(scaffold_plan),
        "stage_manifest": stage_manifest_items(scaffold_plan),
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
