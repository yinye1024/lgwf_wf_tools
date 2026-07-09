"""校验 wf-create 生成出的目标 package 是否真实存在且符合已确认结构。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_relative_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute() or ":" in cleaned:
        raise ValueError(f"{field_name} 禁止绝对路径或盘符路径")
    if any(part in {"..", ".lgwf"} for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..` 或 `.lgwf`")
    return candidate.as_posix().strip("/")


def find_workspace_root(work_dir: Path, implementation_context: dict[str, Any]) -> Path:
    raw = str(implementation_context.get("workspace_root", "")).strip()
    if raw:
        candidate = Path(raw).resolve()
        if candidate.exists():
            return candidate
    current = work_dir.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "skills").is_dir():
            return candidate
    raise RuntimeError(f"无法从运行目录推导 workspace_root: {work_dir}")


def confirmed_step_designs(step_designs: dict[str, Any]) -> dict[str, Any]:
    confirmed = step_designs.get("confirmed")
    if isinstance(confirmed, dict):
        return confirmed
    return step_designs


def required_stage_ids(step_designs: dict[str, Any]) -> list[str]:
    confirmed = confirmed_step_designs(step_designs)
    stages = confirmed.get("source_business_flow_stages", [])
    if not isinstance(stages, list):
        return []
    result: list[str] = []
    for item in stages:
        if not isinstance(item, dict):
            continue
        stage_id = str(item.get("stage_id", "")).strip()
        if stage_id:
            result.append(stage_id)
    return result


def confirmed_step_design_items(step_designs: dict[str, Any]) -> list[dict[str, Any]]:
    confirmed = confirmed_step_designs(step_designs)
    for key in ("step_designs", "step_designs_proposal"):
        items = confirmed.get(key, [])
        if isinstance(items, list) and items:
            return [item for item in items if isinstance(item, dict)]
    return []


def strip_target_package_root(normalized_path: str, target_package_root: str) -> str:
    if not target_package_root:
        return normalized_path
    path_parts = PurePosixPath(normalized_path).parts
    root_parts = PurePosixPath(target_package_root).parts
    if path_parts[: len(root_parts)] != root_parts:
        return normalized_path
    remaining = path_parts[len(root_parts) :]
    if not remaining:
        return ""
    return PurePosixPath(*remaining).as_posix()


def package_relative_path(raw_path: str, field_name: str, target_package_root: str = "") -> str:
    normalized = normalize_relative_path(raw_path, field_name)
    normalized = strip_target_package_root(normalized, target_package_root)
    if normalized.startswith("docs/steps/"):
        return f"wf/{normalized}"
    return normalized


def implementation_generated_files(implementation: dict[str, Any], target_package_root: str) -> list[str]:
    raw_items = implementation.get("generated_files", [])
    if not isinstance(raw_items, list):
        return []
    result: list[str] = []
    for index, item in enumerate(raw_items):
        if isinstance(item, str):
            raw_path = item
        elif isinstance(item, dict):
            raw_path = str(item.get("path", "")).strip()
        else:
            continue
        if raw_path:
            result.append(
                package_relative_path(
                    raw_path,
                    f"implementation.generated_files[{index}].path",
                    target_package_root,
                )
            )
    return result


def implementation_validation_failures(implementation: dict[str, Any]) -> list[str]:
    raw_items = implementation.get("validation", [])
    if not isinstance(raw_items, list):
        return []
    failures: list[str] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "")).strip().lower()
        if status and not status.startswith("passed"):
            command = str(item.get("command", f"validation[{index}]"))
            failures.append(f"implementation_result 自报验证未通过: {command} status={status}")
    return failures


def is_stage_exempt(step_designs: dict[str, Any], stage_id: str, directory_name: str) -> bool:
    confirmed = confirmed_step_designs(step_designs)
    exemptions = confirmed.get("stage_directory_exemptions", {})
    if not isinstance(exemptions, dict):
        return False
    stage_exemptions = exemptions.get(stage_id, [])
    return isinstance(stage_exemptions, list) and directory_name in stage_exemptions


def markdown_mentions_target_dirs(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    return "TARGET_DIRS" in text or "TARGET_FILES" in text


def check_agent_loop_prompt_contracts(target_abs: Path, checks: list[dict[str, Any]], failures: list[str]) -> None:
    for workflow_lgwf in (target_abs / "wf").glob("*/workflow.lgwf"):
        text = workflow_lgwf.read_text(encoding="utf-8-sig")
        if "AGENT_LOOP" not in text:
            continue
        stage_root = workflow_lgwf.parent
        for directory_name in ("agents", "resources"):
            directory = stage_root / directory_name
            if not directory.exists():
                continue
            for md_path in sorted(directory.glob("*.md")):
                ok = not markdown_mentions_target_dirs(md_path)
                checks.append(
                    {
                        "check": "agent_loop_prompt_no_target_dirs_contract",
                        "path": str(md_path),
                        "ok": ok,
                    }
                )
                if not ok:
                    failures.append(
                        f"AGENT_LOOP 阶段文档不得承诺 TARGET_DIRS/TARGET_FILES: {md_path}"
                    )


def run_authoring_audit(workflow_lgwf: Path, workspace_root: Path) -> dict[str, Any]:
    lgwf_py = workspace_root / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
    if not lgwf_py.exists():
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"找不到 lgwf.py: {lgwf_py}",
        }
    completed = subprocess.run(
        [sys.executable, str(lgwf_py), "audit", str(workflow_lgwf)],
        cwd=workspace_root,
        text=True,
        capture_output=True,
    )
    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def validate_created_package(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation = load_json(lgwf_dir / "implementation_result.json")
    implementation_context = load_json(lgwf_dir / "implementation_context.json")
    step_designs = load_json(lgwf_dir / "step_designs.json")

    target_package_root = str(
        implementation.get("target_package_root")
        or implementation_context.get("target_package_root")
        or confirmed_step_designs(step_designs).get("target_package_root")
        or ""
    )
    target_package_root = normalize_relative_path(target_package_root, "target_package_root")
    workspace_root = find_workspace_root(work_dir, implementation_context)
    target_abs = (workspace_root / target_package_root).resolve()
    target_abs.relative_to(workspace_root.resolve())

    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def require_path(path: Path, label: str) -> None:
        ok = path.exists()
        checks.append({"check": label, "path": str(path), "ok": ok})
        if not ok:
            failures.append(f"{label} 不存在: {path}")

    require_path(target_abs, "target_package_root")
    workflow_lgwf = target_abs / "wf" / "workflow.lgwf"
    require_path(workflow_lgwf, "wf/workflow.lgwf")

    for stage_id in required_stage_ids(step_designs):
        stage_root = target_abs / "wf" / stage_id
        require_path(stage_root / "workflow.lgwf", f"stage {stage_id} workflow.lgwf")
        for directory_name in ("agents", "scripts", "resources"):
            if is_stage_exempt(step_designs, stage_id, directory_name):
                checks.append(
                    {
                        "check": f"stage {stage_id} {directory_name}/ exempt",
                        "path": str(stage_root / directory_name),
                        "ok": True,
                    }
                )
                continue
            require_path(stage_root / directory_name, f"stage {stage_id} {directory_name}/")

    for item in confirmed_step_design_items(step_designs):
        raw_path = str(item.get("doc_path") or item.get("path") or "").strip()
        if not raw_path:
            continue
        rel_path = package_relative_path(raw_path, "step_design.path", target_package_root)
        require_path(target_abs / rel_path, f"approved step design {rel_path}")

    for rel_path in implementation_generated_files(implementation, target_package_root):
        require_path(target_abs / rel_path, f"implementation_result generated file {rel_path}")

    for failure in implementation_validation_failures(implementation):
        failures.append(failure)

    check_agent_loop_prompt_contracts(target_abs, checks, failures)

    audit_result: dict[str, Any] = {"ok": False, "skipped": True}
    if workflow_lgwf.exists():
        audit_result = run_authoring_audit(workflow_lgwf, workspace_root)
        checks.append({"check": "lgwf.py audit", "path": str(workflow_lgwf), "ok": audit_result.get("ok")})
        if not audit_result.get("ok"):
            failures.append("lgwf.py audit 未通过")
    else:
        failures.append("缺少 wf/workflow.lgwf，无法运行 lgWF authoring audit")

    result = {
        "status": "passed" if not failures else "failed",
        "target_package_root": target_package_root,
        "target_package_abs": str(target_abs),
        "stage_ids": required_stage_ids(step_designs),
        "checks": checks,
        "audit": audit_result,
        "failures": failures,
    }
    write_json(lgwf_dir / "created_package_validation.json", result)
    if failures:
        raise RuntimeError("created package validation failed: " + "; ".join(failures))
    return result


def main() -> None:
    result = validate_created_package(Path.cwd())
    print(json.dumps({"lgwf_wf_create.created_package_validation": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
