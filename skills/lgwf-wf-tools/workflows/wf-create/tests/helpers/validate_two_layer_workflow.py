from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Iterable


WORKFLOW_REF_RE = re.compile(r'WORKFLOW\s+"([^"]+)"')
RESOURCE_REF_RE = re.compile(r'(SCRIPT|PROMPT|PROMPT_REF|SPEC)\s+"([^"]+)"')
ALLOWED_DEEP_WORKFLOWS = {
    "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf",
}
ALLOWED_DEEP_WORKFLOW_PARENTS = {
    "04_implement_steps_react/01_implement_units/workflow.lgwf": {
        "01_implement_one_unit/workflow.lgwf"
    },
    "04_implement_steps_react/02_repair_implementation_react/workflow.lgwf": {
        "01_reason_repair/workflow.lgwf",
        "02_act_repair/workflow.lgwf",
        "03_observe_repair/workflow.lgwf",
        "04_decide_repair/workflow.lgwf",
    }
}
README_OPTIONAL_WORKFLOWS = {
    "04_implement_steps_react/01_implement_units/workflow.lgwf",
    "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf",
    "04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf",
}


def normalize_ref(raw: str, *, field: str) -> PurePosixPath:
    cleaned = raw.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned:
        raise ValueError(f"{field} 不能为空")
    if path.is_absolute() or ":" in cleaned or any(part == ".." for part in path.parts):
        raise ValueError(f"{field} 只能使用包内相对路径: {raw}")
    return path


def workflow_files(wf_root: Path) -> list[Path]:
    return sorted(path for path in wf_root.rglob("workflow.lgwf") if path.is_file())


def validate_workflow_file_depth(package_root: Path, errors: list[str]) -> None:
    wf_root = package_root / "wf"
    if not (wf_root / "workflow.lgwf").is_file():
        errors.append("缺少 wf/workflow.lgwf")
        return
    for workflow in workflow_files(wf_root):
        relative = workflow.relative_to(wf_root).as_posix()
        depth = len(workflow.relative_to(wf_root).parts)
        if relative == "workflow.lgwf":
            continue
        if depth not in {2, 3} and relative not in ALLOWED_DEEP_WORKFLOWS:
            errors.append(f"workflow 最多允许阶段/子流程两级: wf/{relative}")
        if depth == 3 and relative not in README_OPTIONAL_WORKFLOWS and not (workflow.parent / "README.md").is_file():
            errors.append(f"孙级 workflow 必须有 README.md 说明职责: wf/{relative}")
        if (
            relative in ALLOWED_DEEP_WORKFLOWS
            and relative not in README_OPTIONAL_WORKFLOWS
            and not (workflow.parent / "README.md").is_file()
        ):
            errors.append(f"受控第三层 workflow 必须有 README.md 说明职责: wf/{relative}")


def validate_root_workflow(package_root: Path, errors: list[str]) -> None:
    root_workflow = package_root / "wf" / "workflow.lgwf"
    if not root_workflow.is_file():
        return
    text = root_workflow.read_text(encoding="utf-8")
    for ref in WORKFLOW_REF_RE.findall(text):
        ref_path = normalize_ref(ref, field="root WORKFLOW ref")
        if len(ref_path.parts) != 2 or ref_path.parts[-1] != "workflow.lgwf":
            errors.append(f"根 workflow 只能引用第一层子 workflow: {ref}")
        if not (root_workflow.parent / ref_path).is_file():
            errors.append(f"根 workflow 引用不存在: {ref}")


def validate_child_workflow(package_root: Path, workflow: Path, errors: list[str]) -> None:
    wf_root = package_root / "wf"
    relative = workflow.relative_to(wf_root)
    if relative.as_posix() == "workflow.lgwf":
        return
    stage_dir = workflow.parent
    text = workflow.read_text(encoding="utf-8")
    relative_parts = relative.parts
    is_stage_workflow = len(relative_parts) == 2
    is_subflow_workflow = len(relative_parts) == 3
    is_deep_workflow = relative.as_posix() in ALLOWED_DEEP_WORKFLOWS
    allowed_deep_refs = ALLOWED_DEEP_WORKFLOW_PARENTS.get(relative.as_posix(), set())
    for ref in WORKFLOW_REF_RE.findall(text):
        ref_path = normalize_ref(ref, field=f"WORKFLOW ref in wf/{relative.as_posix()}")
        if is_stage_workflow:
            is_local_lgwf_file = len(ref_path.parts) == 1 and ref_path.suffix == ".lgwf"
            is_subflow_workflow = len(ref_path.parts) == 2 and ref_path.parts[-1] == "workflow.lgwf"
            if not (is_local_lgwf_file or is_subflow_workflow):
                errors.append(f"阶段 workflow 只能引用同目录 .lgwf 或同阶段孙级 workflow: wf/{relative.as_posix()} -> {ref}")
                continue
        elif is_subflow_workflow and ref not in allowed_deep_refs:
            errors.append(f"孙级 workflow 不得继续引用 workflow: wf/{relative.as_posix()} -> {ref}")
            continue
        elif is_deep_workflow:
            errors.append(f"受控第三层 workflow 不得继续引用 workflow: wf/{relative.as_posix()} -> {ref}")
            continue
        if not (stage_dir / ref_path).is_file():
            errors.append(f"workflow 引用不存在: wf/{relative.as_posix()} -> {ref}")
    for field, ref in RESOURCE_REF_RE.findall(text):
        ref_path = normalize_ref(ref, field=f"resource ref in wf/{relative.as_posix()}")
        resolved = stage_dir / ref_path
        if field == "SCRIPT":
            shared_scripts = package_root / "wf" / "shared" / "scripts"
            try:
                resolved.relative_to(stage_dir)
            except ValueError:
                try:
                    resolved.relative_to(shared_scripts)
                except ValueError:
                    errors.append(
                        f"子 workflow SCRIPT 只能引用本阶段目录或 wf/shared/scripts: wf/{relative.as_posix()} -> {ref}"
                    )
                    continue
        else:
            try:
                resolved.relative_to(stage_dir)
            except ValueError:
                errors.append(f"子 workflow prompt/spec 引用必须留在本阶段目录: wf/{relative.as_posix()} -> {ref}")
                continue
        if not resolved.exists():
            errors.append(f"子 workflow 资源引用不存在: wf/{relative.as_posix()} -> {ref}")


def validate_no_source_tests_under_wf(package_root: Path, errors: list[str]) -> None:
    if (package_root / "wf" / "tests").exists():
        errors.append("源码测试目录必须放在 package 外层 tests/，不得放入 wf/tests")


def validate_shared_prompt_boundary(package_root: Path, errors: list[str]) -> None:
    shared_root = package_root / "wf" / "shared"
    if not shared_root.exists():
        return
    for path in shared_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".lgwf"}:
            errors.append(f"共享目录只允许脚本/helper，不得放 prompt 或 workflow: {path.relative_to(package_root).as_posix()}")


def validate_package(package_root: Path) -> list[str]:
    errors: list[str] = []
    if not package_root.exists():
        return [f"package root 不存在: {package_root}"]
    validate_workflow_file_depth(package_root, errors)
    validate_root_workflow(package_root, errors)
    for workflow in workflow_files(package_root / "wf"):
        validate_child_workflow(package_root, workflow, errors)
    validate_no_source_tests_under_wf(package_root, errors)
    validate_shared_prompt_boundary(package_root, errors)
    return errors


def validate_scaffold_paths(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    normalized_items: list[tuple[str, PurePosixPath]] = []
    normalized_paths: set[str] = set()
    for raw in list(paths):
        try:
            path = normalize_ref(raw, field="scaffold path")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        normalized_items.append((raw, path))
        normalized_paths.add(path.as_posix())
    for raw, path in normalized_items:
        if path.name == "workflow.lgwf" and path.parts and path.parts[0] == "wf":
            if len(path.parts) > 4:
                errors.append(f"scaffold 计划 workflow 最多允许阶段/子流程两级: {raw}")
            if len(path.parts) == 4:
                readme_path = path.parent / "README.md"
                if readme_path.as_posix() not in normalized_paths:
                    errors.append(f"scaffold 计划孙级 workflow 必须包含 README.md: {raw}")
        if path.parts[:2] == ("wf", "tests"):
            errors.append(f"scaffold 计划禁止 wf/tests: {raw}")
        if len(path.parts) >= 3 and path.parts[:2] == ("wf", "shared") and path.suffix.lower() in {".md", ".lgwf"}:
            errors.append(f"scaffold 计划禁止在 wf/shared 放 prompt 或 workflow: {raw}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 workflow package 的受控模块化 workflow 结构。")
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    args = parser.parse_args()
    errors = validate_package(args.package_root)
    result = {"passed": not errors, "errors": errors, "package_root": str(args.package_root)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
        else:
            print("workflow structure validation passed")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
