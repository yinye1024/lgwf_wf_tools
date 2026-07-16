"""对 wf-create 生成出的目标 workflow package 执行确定性 observe audit。"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


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


def strip_target_package_root(normalized_path: str, target_package_root: str) -> str:
    if not target_package_root:
        return normalized_path
    path_parts = PurePosixPath(normalized_path).parts
    root_parts = PurePosixPath(target_package_root).parts
    if path_parts[: len(root_parts)] != root_parts:
        return normalized_path
    remaining = path_parts[len(root_parts) :]
    return PurePosixPath(*remaining).as_posix() if remaining else ""


def package_relative_path(raw_path: str, field_name: str, target_package_root: str = "") -> str:
    normalized = normalize_relative_path(raw_path, field_name)
    return strip_target_package_root(normalized, target_package_root)


def confirmed_step_designs(step_designs: dict[str, Any]) -> dict[str, Any]:
    confirmed = step_designs.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else step_designs


def required_stage_ids(step_designs: dict[str, Any]) -> list[str]:
    confirmed = confirmed_step_designs(step_designs)
    stages = confirmed.get("source_business_flow_stages", [])
    if not isinstance(stages, list):
        return []
    result: list[str] = []
    for item in stages:
        if isinstance(item, dict):
            stage_id = str(item.get("stage_id", "")).strip()
            if stage_id:
                result.append(stage_id)
    return result


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
    return unique(result)


def step_design_paths(step_designs: dict[str, Any], section: str, fallback_field: str) -> list[str]:
    confirmed = confirmed_step_designs(step_designs)
    result: list[str] = []
    raw_designs = confirmed.get(section, [])
    if isinstance(raw_designs, list):
        for index, item in enumerate(raw_designs):
            if not isinstance(item, dict):
                continue
            raw_path = str(item.get("path", "")).strip()
            if raw_path:
                result.append(package_relative_path(raw_path, f"{section}[{index}].path"))
    raw_steps = confirmed.get("step_designs", [])
    if not isinstance(raw_steps, list) or not raw_steps:
        raw_steps = confirmed.get("step_designs_proposal", [])
    if isinstance(raw_steps, list):
        for step_index, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            raw_paths = item.get(fallback_field, [])
            if not isinstance(raw_paths, list):
                continue
            for path_index, raw_path in enumerate(raw_paths):
                if str(raw_path).strip():
                    result.append(package_relative_path(str(raw_path), f"step_designs[{step_index}].{fallback_field}[{path_index}]"))
    return unique(result)


def step_design_file_entries(step_designs: dict[str, Any]) -> list[dict[str, Any]]:
    confirmed = confirmed_step_designs(step_designs)
    raw_designs = confirmed.get("file_designs", [])
    if not isinstance(raw_designs, list):
        return []
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_designs):
        if not isinstance(item, dict):
            continue
        raw_path = str(item.get("path", "")).strip()
        if not raw_path:
            continue
        rel_path = package_relative_path(raw_path, f"file_designs[{index}].path")
        if not rel_path or rel_path in seen:
            continue
        seen.add(rel_path)
        entries.append({**item, "path": rel_path})
    return entries


def stage_dirs_from_step_designs(step_designs: dict[str, Any]) -> list[str]:
    stage_dirs: list[str] = []
    for rel_path in step_design_paths(step_designs, "file_designs", "target_files"):
        parts = PurePosixPath(rel_path).parts
        if len(parts) >= 3 and parts[0] == "wf" and parts[1] not in {"docs", "shared"}:
            stage_dirs.append(parts[1])
    for rel_path in step_design_paths(step_designs, "directory_designs", "target_dirs"):
        parts = PurePosixPath(rel_path).parts
        if len(parts) >= 2 and parts[0] == "wf" and parts[1] not in {"docs", "shared"}:
            stage_dirs.append(parts[1])
    return unique(stage_dirs)


def implementation_status_failures(implementation: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    status = str(implementation.get("status", "")).strip().lower()
    if status in {"failed", "partial", "error", "needs_review"}:
        failures.append(f"implementation_result 自报状态未通过: status={status}")
    failed_units = implementation.get("failed_units", [])
    if isinstance(failed_units, list):
        failures.extend([f"implementation_result 存在失败 unit: {unit}" for unit in failed_units if str(unit).strip()])
    remaining_risks = implementation.get("remaining_risks", [])
    if isinstance(remaining_risks, list):
        failures.extend([f"implementation_result 存在未关闭风险: {risk}" for risk in remaining_risks if str(risk).strip()])
    return failures


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


def repair_round_failures(implementation: dict[str, Any]) -> list[str]:
    raw_rounds = implementation.get("repair_rounds", [])
    if not isinstance(raw_rounds, list) or not raw_rounds:
        return []
    latest = raw_rounds[-1]
    if not isinstance(latest, dict):
        return []
    status = str(latest.get("status", "")).strip().lower()
    if status not in {"invalid_plan", "blocked"}:
        return []
    failures: list[str] = []
    raw_failures = latest.get("failures", [])
    if isinstance(raw_failures, list):
        failures.extend([f"repair_round {status}: {item}" for item in raw_failures if str(item).strip()])
    raw_risks = latest.get("remaining_risks", [])
    if isinstance(raw_risks, list):
        failures.extend([f"repair_round {status}: {item}" for item in raw_risks if str(item).strip()])
    if not failures:
        failures.append(f"repair_round {status}: 修复未发布")
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
    wf_root = target_abs / "wf"
    if not wf_root.exists():
        return
    for workflow_lgwf in wf_root.glob("*/workflow.lgwf"):
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
                    failures.append(f"AGENT_LOOP 阶段文档不得承诺 TARGET_DIRS/TARGET_FILES: {md_path}")


def check_runtime_pollution(target_abs: Path, checks: list[dict[str, Any]], failures: list[str]) -> None:
    forbidden_dirs = {".lgwf", ".tmp", "__pycache__"}
    for path in sorted(target_abs.rglob("*")):
        if not path.is_dir() or path.name not in forbidden_dirs:
            continue
        checks.append({"check": "target_package_no_runtime_pollution", "path": str(path), "ok": False})
        failures.append(f"目标 package 不得包含运行态目录: {path}")


REFERENCE_PATTERN = re.compile(r'\b(SCRIPT|PROMPT|PROMPT_REF|SPEC|WORKFLOW)\s+"([^"]+)"')


def normalize_workflow_reference(raw_path: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned:
        raise ValueError("引用路径不能为空")
    if candidate.is_absolute() or ":" in cleaned:
        raise ValueError("引用路径禁止绝对路径或盘符路径")
    if any(part in {"..", ".lgwf"} for part in candidate.parts):
        raise ValueError("引用路径禁止 `..` 或 `.lgwf`")
    return candidate.as_posix()


def check_workflow_resource_references(target_abs: Path, checks: list[dict[str, Any]], failures: list[str]) -> None:
    for workflow_lgwf in sorted((target_abs / "wf").rglob("workflow.lgwf")):
        text = workflow_lgwf.read_text(encoding="utf-8-sig")
        for kind, raw_path in REFERENCE_PATTERN.findall(text):
            try:
                rel_path = normalize_workflow_reference(raw_path)
            except ValueError as exc:
                checks.append(
                    {
                        "check": "workflow_reference_path",
                        "path": f"{workflow_lgwf}:{raw_path}",
                        "ok": False,
                    }
                )
                failures.append(f"{workflow_lgwf} 的 {kind} 引用非法: {raw_path} ({exc})")
                continue
            target = workflow_lgwf.parent / rel_path
            ok = target.is_file()
            checks.append(
                {
                    "check": f"workflow_reference_exists:{kind}",
                    "path": str(target),
                    "ok": ok,
                }
            )
            if not ok:
                failures.append(f"{workflow_lgwf} 的 {kind} 引用文件不存在: {rel_path}")


TEXT_EXTENSIONS = {".lgwf", ".md", ".py", ".json", ".yaml", ".yml"}


PLACEHOLDER_JSON_PATTERN = re.compile(r'"_lgwf_placeholder"\s*:\s*true')


def normalized_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def check_step_design_content_contracts(target_abs: Path, step_designs: dict[str, Any], checks: list[dict[str, Any]], failures: list[str]) -> None:
    for item in step_design_file_entries(step_designs):
        rel_path = str(item.get("path", "")).strip()
        if not rel_path:
            continue
        path = target_abs / rel_path
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="replace")

        placeholder_ok = "LGWF_PLACEHOLDER" not in text and PLACEHOLDER_JSON_PATTERN.search(text) is None
        checks.append({"check": "generated_file_not_placeholder", "path": str(path), "ok": placeholder_ok})
        if not placeholder_ok:
            failures.append(f"生成文件仍包含占位内容，必须由实现阶段替换: {rel_path}")

        if str(item.get("content_mode", "")).strip() != "exact":
            continue
        expected = item.get("exact_content")
        if not isinstance(expected, str) or not expected.strip():
            continue
        exact_ok = normalized_text(text) == normalized_text(expected)
        checks.append({"check": "exact_content_matches_step_design", "path": str(path), "ok": exact_ok})
        if not exact_ok:
            failures.append(f"exact 文件内容与 step_designs.file_designs[].exact_content 不一致: {rel_path}")


def check_utf8_no_bom(target_abs: Path, checks: list[dict[str, Any]], failures: list[str]) -> None:
    for path in sorted(target_abs.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            checks.append({"check": "text_utf8_no_bom", "path": str(path), "ok": False})
            failures.append(f"文本文件不得包含 UTF-8 BOM: {path}")
            continue
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            checks.append({"check": "text_utf8_no_bom", "path": str(path), "ok": False})
            failures.append(f"文本文件必须使用 UTF-8: {path} ({exc})")
            continue
        checks.append({"check": "text_utf8_no_bom", "path": str(path), "ok": True})


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


def run_authoring_audit(workflow_lgwf: Path, workspace_root: Path) -> dict[str, Any]:
    try:
        rel_input = workflow_lgwf.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError as exc:
        return {
            "ok": False,
            "skipped": True,
            "exit_code": None,
            "stdout": "",
            "stderr": f"workflow_lgwf 不在 workspace_root 内: {workflow_lgwf} ({exc})",
        }
    try:
        import lgwf_client.tools.registry as tool_registry_module
    except Exception as exc:  # pragma: no cover - runtime 环境异常时保留可诊断结果
        return {
            "ok": False,
            "skipped": True,
            "exit_code": None,
            "stdout": "",
            "stderr": f"无法加载 runtime tool registry: {type(exc).__name__}: {exc}",
        }
    tool_result = tool_registry_module.run_builtin_tool(
        "lgwf_dsl_cli",
        {
            "command": "audit",
            "input": rel_input,
            "include_stdout": True,
            "fail_on_command_failure": False,
        },
        workspace_root.resolve(),
    )
    return {
        "ok": bool(tool_result.get("passed")),
        "skipped": False,
        "exit_code": tool_result.get("exit_code"),
        "stdout": str(tool_result.get("stdout", "")),
        "stderr": str(tool_result.get("stderr", "")),
        "tool": "lgwf_dsl_cli",
        "command": "audit",
        "payload": tool_result.get("payload", {}),
        "diagnostics": tool_result.get("diagnostics", []),
    }


def audit_result_from_tool_output(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "ok": False,
            "skipped": True,
            "exit_code": None,
            "stdout": "",
            "stderr": f"缺少 TOOL audit 输出: {path.as_posix()}",
            "tool": "lgwf_dsl_cli",
            "command": "audit",
            "payload": {},
            "diagnostics": [],
        }
    try:
        tool_result = read_json(path)
    except Exception as exc:
        return {
            "ok": False,
            "skipped": True,
            "exit_code": None,
            "stdout": "",
            "stderr": f"TOOL audit 输出不可解析: {type(exc).__name__}: {exc}",
            "tool": "lgwf_dsl_cli",
            "command": "audit",
            "payload": {},
            "diagnostics": [],
        }
    return {
        "ok": bool(tool_result.get("passed")),
        "skipped": False,
        "exit_code": tool_result.get("exit_code"),
        "stdout": str(tool_result.get("stdout", "")),
        "stderr": str(tool_result.get("stderr", "")),
        "tool": "lgwf_dsl_cli",
        "command": "audit",
        "payload": tool_result.get("payload", {}),
        "diagnostics": tool_result.get("diagnostics", []),
        "tool_result_file": path.as_posix(),
    }


def package_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def collect_workflow_audits(
    target_abs: Path,
    workspace_root: Path,
    root_workflow: Path,
    root_audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    wf_root = target_abs / "wf"
    candidates: list[Path] = []
    if root_workflow.exists():
        candidates.append(root_workflow)
    if wf_root.is_dir():
        for candidate in sorted(wf_root.rglob("workflow.lgwf")):
            if candidate.resolve() != root_workflow.resolve():
                candidates.append(candidate)

    results: list[dict[str, Any]] = []
    for candidate in candidates:
        if root_audit is not None and candidate.resolve() == root_workflow.resolve():
            audit = root_audit
        else:
            audit = run_authoring_audit(candidate, workspace_root)
        item = {
            "package_relative_path": package_relative(candidate, target_abs),
            "path": str(candidate),
            **audit,
        }
        results.append(item)
    return results


def audit_current_implementation(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    implementation_result = read_json(lgwf_dir / "implementation_result.json")
    step_designs = read_json(lgwf_dir / "step_designs.json")
    workspace_root = find_workspace_root(work_dir, implementation_context)

    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    raw_target_package_root = str(
        implementation_result.get("target_package_root")
        or implementation_context.get("target_package_root")
        or confirmed_step_designs(step_designs).get("target_package_root")
        or ""
    )
    try:
        target_package_root = normalize_relative_path(raw_target_package_root, "target_package_root")
    except ValueError as exc:
        target_package_root = ""
        failures.append(str(exc))

    target_abs = (workspace_root / target_package_root).resolve() if target_package_root else workspace_root
    if target_package_root:
        try:
            target_abs.relative_to(workspace_root.resolve())
        except ValueError:
            failures.append(f"target_package_root 越界: {target_package_root}")

    def require_path(path: Path, label: str, kind: str = "exists") -> None:
        if kind == "dir":
            ok = path.is_dir()
        elif kind == "file":
            ok = path.is_file()
        else:
            ok = path.exists()
        checks.append({"check": label, "path": str(path), "ok": ok})
        if not ok:
            failures.append(f"{label} 不存在: {path}")

    require_path(target_abs, "target_package_root", "dir")
    require_path(target_abs / "AGENTS.md", "package AGENTS.md", "file")
    require_path(target_abs / "README.md", "package README.md", "file")
    require_path(target_abs / "entry_contract.json", "package entry_contract.json", "file")
    workflow_lgwf = target_abs / "wf" / "workflow.lgwf"
    require_path(workflow_lgwf, "wf/workflow.lgwf", "file")
    require_path(target_abs / "wf" / "artifact_contracts.json", "wf/artifact_contracts.json", "file")

    for rel_path in implementation_generated_files(implementation_result, target_package_root):
        require_path(target_abs / rel_path, f"implementation_result generated file {rel_path}", "file")

    for rel_path in step_design_paths(step_designs, "file_designs", "target_files"):
        require_path(target_abs / rel_path, f"step_designs file_design {rel_path}", "file")
    for rel_path in step_design_paths(step_designs, "directory_designs", "target_dirs"):
        require_path(target_abs / rel_path, f"step_designs directory_design {rel_path}", "dir")

    failures.extend(implementation_status_failures(implementation_result))
    failures.extend(implementation_validation_failures(implementation_result))
    failures.extend(repair_round_failures(implementation_result))
    check_agent_loop_prompt_contracts(target_abs, checks, failures)
    check_runtime_pollution(target_abs, checks, failures)
    check_workflow_resource_references(target_abs, checks, failures)
    check_step_design_content_contracts(target_abs, step_designs, checks, failures)
    check_utf8_no_bom(target_abs, checks, failures)

    audit_result: dict[str, Any] = {"ok": False, "skipped": True, "stdout": "", "stderr": "", "exit_code": None}
    workflow_audits: list[dict[str, Any]] = []
    if workflow_lgwf.exists():
        audit_result = audit_result_from_tool_output(lgwf_dir / "implementation_lgwf_dsl_audit_result.json")
        checks.append({"check": "lgwf_dsl_cli audit", "path": str(workflow_lgwf), "ok": audit_result.get("ok")})
        if not audit_result.get("ok"):
            failures.append("lgwf_dsl_cli audit 未通过")
        workflow_audits = collect_workflow_audits(target_abs, workspace_root, workflow_lgwf, audit_result)
        for item in workflow_audits:
            rel_path = str(item.get("package_relative_path", ""))
            ok = bool(item.get("ok"))
            checks.append({"check": f"lgwf_dsl_cli audit {rel_path}", "path": item.get("path", ""), "ok": ok})
            if not ok and rel_path != "wf/workflow.lgwf":
                failures.append(f"lgwf_dsl_cli audit 未通过: {rel_path}")
    else:
        failures.append("缺少 wf/workflow.lgwf，无法运行 LGWF authoring audit")

    needs_post_fix = bool(
        workflow_lgwf.exists()
        and (
            not audit_result.get("ok")
            or any(not item.get("ok") for item in workflow_audits)
        )
    )

    result = {
        "passed": not failures,
        "status": "passed" if not failures else "failed",
        "target_package_root": target_package_root,
        "target_package_abs": str(target_abs),
        "workflow_lgwf": str(workflow_lgwf),
        "stage_ids": required_stage_ids(step_designs),
        "stage_dirs": stage_dirs_from_step_designs(step_designs),
        "design_source": ".lgwf/step_designs.json",
        "checks": checks,
        "audit": audit_result,
        "workflow_audits": workflow_audits,
        "failures": failures,
        "needs_post_fix": needs_post_fix,
    }
    write_json(lgwf_dir / "implementation_audit_result.json", result)
    write_json(lgwf_dir / "implementation_observe.json", result)
    return result


def main() -> None:
    result = audit_current_implementation(Path.cwd())
    print(json.dumps({"lgwf_wf_create.implementation_audit_result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
