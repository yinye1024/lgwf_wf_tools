"""把已确认步骤设计拆成可由 FOREACH 独立处理的 implementation units。"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


PACKAGE_CONTRACT_FILE_ALLOWLIST = {
    "AGENTS.md",
    "README.md",
    "entry_contract.json",
    "wf/artifact_contracts.json",
}
IGNORED_WF_STAGE_DIRS = {"docs", "shared"}


def load_json(path: Path) -> dict[str, Any]:
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


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def slugify(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    return cleaned or fallback


def normalize_package_path(raw_path: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
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


def direct_parent_dirs_for_files(files: list[str]) -> list[str]:
    dirs: list[str] = []
    for raw_path in files:
        path = PurePosixPath(normalize_package_path(raw_path))
        parent = path.parent.as_posix()
        dirs.append("." if parent == "." else parent)
    return unique(dirs)


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


def file_design_items(step_designs: dict[str, Any]) -> list[dict[str, Any]]:
    return as_dict_list(confirmed_payload(step_designs).get("file_designs", []))


def directory_design_items(step_designs: dict[str, Any]) -> list[dict[str, Any]]:
    return as_dict_list(confirmed_payload(step_designs).get("directory_designs", []))


def selected_designs_by_path(items: list[dict[str, Any]], paths: list[str]) -> list[dict[str, Any]]:
    expected = {normalize_package_path(path) for path in paths}
    selected: list[dict[str, Any]] = []
    for item in items:
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        try:
            normalized = normalize_package_path(raw_path)
        except ValueError:
            continue
        if normalized in expected:
            selected.append(item)
    return selected


def design_paths(items: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for item in items:
        raw_path = item.get("path")
        if isinstance(raw_path, str) and raw_path.strip():
            paths.append(normalize_package_path(raw_path))
    return unique(paths)


def step_target_paths(items: list[dict[str, Any]], field: str) -> list[str]:
    paths: list[str] = []
    for item in items:
        value = item.get(field)
        if not isinstance(value, list):
            continue
        for raw_path in value:
            if isinstance(raw_path, str) and raw_path.strip():
                paths.append(normalize_package_path(raw_path))
    return unique(paths)


def package_design_files(file_paths: list[str]) -> list[str]:
    return [
        path
        for path in file_paths
        if path in PACKAGE_CONTRACT_FILE_ALLOWLIST or ("/" not in path and not path.startswith("tests"))
    ]


def root_workflow_files(file_paths: list[str]) -> list[str]:
    return [path for path in file_paths if path == "wf/workflow.lgwf"]


def support_design_files(file_paths: list[str]) -> list[str]:
    return [path for path in file_paths if path.startswith("tests/") or path.startswith("wf/shared/")]


def support_design_dirs(dir_paths: list[str]) -> list[str]:
    return [
        path
        for path in dir_paths
        if path == "tests" or path.startswith("tests/") or path == "wf/shared" or path.startswith("wf/shared/")
    ]


def stage_dir_from_file_path(raw_path: str) -> str:
    path = PurePosixPath(normalize_package_path(raw_path))
    parts = path.parts
    if len(parts) >= 3 and parts[0] == "wf" and parts[1] not in IGNORED_WF_STAGE_DIRS:
        return parts[1]
    return ""


def stage_dir_from_dir_path(raw_path: str) -> str:
    path = PurePosixPath(normalize_package_path(raw_path))
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "wf" and parts[1] not in IGNORED_WF_STAGE_DIRS:
        return parts[1]
    return ""


def stage_dir_for_step(item: dict[str, Any], fallback_index: int) -> str:
    stage_id = str(item.get("stage_id") or item.get("stage") or "").strip()
    target_files = step_target_paths([item], "target_files")
    for rel_path in target_files:
        stage_dir = stage_dir_from_file_path(rel_path)
        if stage_dir and rel_path == f"wf/{stage_dir}/workflow.lgwf":
            return stage_dir
    for rel_path in target_files:
        stage_dir = stage_dir_from_file_path(rel_path)
        if stage_dir:
            return stage_dir
    for rel_path in step_target_paths([item], "target_dirs"):
        stage_dir = stage_dir_from_dir_path(rel_path)
        if stage_dir:
            return stage_dir
    return numbered_stage_dir(fallback_index, slugify(stage_id, f"stage_{fallback_index:02d}"))


def stage_groups(
    step_designs_payload: dict[str, Any],
    step_items: list[dict[str, Any]],
    file_paths: list[str],
    dir_paths: list[str],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    by_dir: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(step_items, start=1):
        stage_id = slugify(
            str(item.get("stage_id") or item.get("stage") or "").strip(),
            f"stage_{index:02d}",
        )
        stage_dir = stage_dir_for_step(item, index)
        group = by_dir.get(stage_dir)
        if group is None:
            group = {"stage_id": stage_id, "stage_dir": stage_dir, "step_designs": []}
            by_dir[stage_dir] = group
            groups.append(group)
        group["step_designs"].append(item)

    for rel_path in file_paths:
        stage_dir = stage_dir_from_file_path(rel_path)
        if not stage_dir or stage_dir in by_dir:
            continue
        stage_id = slugify(strip_numeric_prefix(stage_dir), strip_numeric_prefix(stage_dir) or stage_dir)
        group = {"stage_id": stage_id, "stage_dir": stage_dir, "step_designs": []}
        by_dir[stage_dir] = group
        groups.append(group)
    for rel_path in dir_paths:
        stage_dir = stage_dir_from_dir_path(rel_path)
        if not stage_dir or stage_dir in by_dir:
            continue
        stage_id = slugify(strip_numeric_prefix(stage_dir), strip_numeric_prefix(stage_dir) or stage_dir)
        group = {"stage_id": stage_id, "stage_dir": stage_dir, "step_designs": []}
        by_dir[stage_dir] = group
        groups.append(group)

    if groups:
        return groups

    return [
        {"stage_id": stage_id, "stage_dir": numbered_stage_dir(index, stage_id), "step_designs": []}
        for index, stage_id in enumerate(source_stage_ids(step_designs_payload), start=1)
    ]


def stage_path_filter(paths: list[str], stage_dir: str, *, directory: bool = False) -> list[str]:
    selected: list[str] = []
    for path in paths:
        candidate_stage_dir = stage_dir_from_dir_path(path) if directory else stage_dir_from_file_path(path)
        if candidate_stage_dir == stage_dir:
            selected.append(path)
    return unique(selected)


def unit_payload(
    *,
    unit_id: str,
    unit_type: str,
    objective: str,
    package_relative_files: list[str],
    package_relative_dirs: list[str],
    implementation_context: dict[str, Any],
    step_designs: list[dict[str, Any]],
    file_designs: list[dict[str, Any]] | None = None,
    directory_designs: list[dict[str, Any]] | None = None,
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
        "output_files": package_relative_files,
        "output_dirs": package_relative_dirs,
        "step_designs": step_designs,
        "file_designs": file_designs or [],
        "directory_designs": directory_designs or [],
    }
    if extra:
        payload.update(extra)
    return payload


def all_units(
    implementation_context: dict[str, Any],
    step_designs_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    items = step_design_items(step_designs_payload)
    file_designs = file_design_items(step_designs_payload)
    directory_designs = directory_design_items(step_designs_payload)
    file_design_paths = design_paths(file_designs)
    directory_design_paths = design_paths(directory_designs)
    package_files = package_design_files(file_design_paths)
    package_dirs = direct_parent_dirs_for_files(package_files)
    root_files = root_workflow_files(file_design_paths)
    root_dirs = direct_parent_dirs_for_files(root_files)
    support_unit_files = support_design_files(file_design_paths)
    support_unit_dirs_from_design = support_design_dirs(directory_design_paths)
    allocated_dirs = unique([*package_dirs, *root_dirs])
    allocated_files = unique([*package_files, *root_files, *support_unit_files])
    units: list[dict[str, Any]] = []
    if package_files or package_dirs:
        units.append(
            unit_payload(
                unit_id="package_contracts",
                unit_type="package",
                objective="按已确认文件级设计生成或修复目标 package 入口文档、入口契约和 artifact contract。",
                package_relative_files=package_files,
                package_relative_dirs=package_dirs,
                implementation_context=implementation_context,
                step_designs=items,
                file_designs=selected_designs_by_path(file_designs, package_files),
                directory_designs=selected_designs_by_path(directory_designs, package_dirs),
                extra={
                    "package_profile": implementation_context.get("package_profile", ""),
                    "planned_files": package_files,
                    "planned_dirs": package_dirs,
                },
            )
        )
    if root_files or root_dirs:
        units.append(
            unit_payload(
                unit_id="root_workflow",
                unit_type="root_workflow",
                objective="按已确认步骤设计 JSON 生成或修复根 wf/workflow.lgwf。",
                package_relative_files=root_files,
                package_relative_dirs=root_dirs,
                implementation_context=implementation_context,
                step_designs=items,
                file_designs=selected_designs_by_path(file_designs, root_files),
                directory_designs=selected_designs_by_path(directory_designs, root_dirs),
                extra={
                    "planned_files": root_files,
                    "planned_dirs": root_dirs,
                },
            )
        )

    for group in stage_groups(step_designs_payload, items, file_design_paths, directory_design_paths):
        stage_dir = str(group.get("stage_dir", "")).strip()
        if not stage_dir:
            continue
        stage_items = as_dict_list(group.get("step_designs", []))
        stage_target_files = stage_path_filter(step_target_paths(stage_items, "target_files"), stage_dir)
        stage_target_dirs = stage_path_filter(step_target_paths(stage_items, "target_dirs"), stage_dir, directory=True)
        stage_design_files = stage_path_filter(file_design_paths, stage_dir)
        stage_design_dirs = stage_path_filter(directory_design_paths, stage_dir, directory=True)
        planned_files = unique([*stage_target_files, *stage_design_files])
        planned_dirs = unique(
            [
                *stage_target_dirs,
                *stage_design_dirs,
                *direct_parent_dirs_for_files(planned_files),
            ]
        )
        if not planned_files and not planned_dirs:
            continue
        allocated_dirs = unique([*allocated_dirs, *planned_dirs])
        allocated_files = unique([*allocated_files, *planned_files])
        workflow_ref = f"wf/{stage_dir}/workflow.lgwf"
        units.append(
            unit_payload(
                unit_id=f"stage_{stage_dir}",
                unit_type="stage",
                objective=f"按已确认文件级和步骤级设计生成或修复阶段 `{stage_dir}` 的自包含 workflow、prompt、script 和 resource。",
                package_relative_files=planned_files,
                package_relative_dirs=planned_dirs,
                implementation_context=implementation_context,
                step_designs=stage_items,
                file_designs=selected_designs_by_path(file_designs, planned_files),
                directory_designs=selected_designs_by_path(directory_designs, planned_dirs),
                extra={
                    "stage_id": group.get("stage_id", ""),
                    "stage_dir": stage_dir,
                    "workflow_ref": workflow_ref,
                    "planned_files": planned_files,
                    "planned_dirs": planned_dirs,
                },
            )
        )

    unallocated_design_files = [path for path in file_design_paths if path not in set(allocated_files)]
    unallocated_design_dirs = [path for path in directory_design_paths if path not in set(allocated_dirs)]
    support_unit_files = unique([*support_unit_files, *unallocated_design_files])
    support_unit_output_dirs = unique(
        [
            *support_unit_dirs_from_design,
            *unallocated_design_dirs,
            *direct_parent_dirs_for_files(support_unit_files),
        ]
    )
    if support_unit_files or support_unit_output_dirs:
        units.append(
            unit_payload(
                unit_id="shared_helpers_tests",
                unit_type="support",
                objective="按已确认文件级设计生成或修复共享 helper、最小测试和验证辅助文件。",
                package_relative_files=support_unit_files,
                package_relative_dirs=support_unit_output_dirs,
                implementation_context=implementation_context,
                step_designs=[],
                file_designs=selected_designs_by_path(file_designs, support_unit_files),
                directory_designs=selected_designs_by_path(directory_designs, support_unit_output_dirs),
                extra={
                    "planned_files": support_unit_files,
                    "planned_dirs": support_unit_output_dirs,
                },
            )
        )
    return units


def build_implementation_units(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    implementation_context = load_json(lgwf_dir / "implementation_context.json")
    step_designs_payload = load_json(lgwf_dir / "step_designs.json")
    units = all_units(
        implementation_context,
        step_designs_payload,
    )
    result = {
        "selection_mode": "full",
        "design_source": ".lgwf/step_designs.json",
        "unit_count": len(units),
        "implementation_units": units,
        "all_unit_ids": [str(unit.get("unit_id", "")) for unit in units],
        "failure_count": 0,
        "failures": [],
        "stage_groups": [
            {"stage_id": unit.get("stage_id", ""), "stage_dir": unit.get("stage_dir", "")}
            for unit in units
            if unit.get("unit_type") == "stage"
        ],
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
