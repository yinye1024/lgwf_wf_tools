from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


WF_POST_FIX_LGWF = "skills/lgwf-wf-tools/workflows/wf-post-fix/wf/workflow.lgwf"
WF_POST_FIX_WORK_DIR = "skills/lgwf-wf-tools/workflows/wf-post-fix/ws"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def workflow_lgwf_from_package_root(package_root: str) -> str:
    cleaned = package_root.replace("\\", "/").rstrip("/")
    if not cleaned:
        raise ValueError("target_package_root 不能为空")
    return f"{cleaned}/wf/workflow.lgwf"


def build_handoff_payload(summary: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    package_root = str(summary.get("target_package_root", "")).strip()
    if not package_root:
        raise ValueError("summary_result 缺少 target_package_root")
    target_workflow_lgwf = workflow_lgwf_from_package_root(package_root)
    input_payload = {
        "post_fix_target": {
            "target_workflow_lgwf": target_workflow_lgwf,
            "target_package_root": package_root,
            "target_dirs": [package_root],
            "mode": "manual",
        }
    }
    input_json_file = work_dir / ".lgwf" / "post_fix_handoff_input.json"
    input_json_file.parent.mkdir(parents=True, exist_ok=True)
    input_json_file.write_text(json.dumps(input_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_artifacts = [target_workflow_lgwf]
    report_path = str(summary.get("report_path", "")).strip()
    if report_path:
        source_artifacts.append(report_path)
    audit_result = load_json(work_dir / ".lgwf" / "implementation_audit_result.json")
    observe_result = load_json(work_dir / ".lgwf" / "implementation_observe.json")
    diagnostic_artifacts = [
        path
        for path in (
            ".lgwf/implementation_audit_result.json",
            ".lgwf/implementation_observe.json",
        )
        if (work_dir / path).exists()
    ]
    suggested_command = (
        "python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py run "
        f"--workflow-lgwf {WF_POST_FIX_LGWF} "
        f"--work-dir {WF_POST_FIX_WORK_DIR} "
        f"--input-json-file {input_json_file.as_posix()} --background"
    )
    return {
        "workflow_id": "wf-post-fix",
        "next_workflow_id": "wf-post-fix",
        "next_action": "start_workflow",
        "workflow_lgwf": WF_POST_FIX_LGWF,
        "work_dir": WF_POST_FIX_WORK_DIR,
        "input_json_file": input_json_file.as_posix(),
        "suggested_command": suggested_command,
        "source_artifacts": source_artifacts,
        "diagnostic_artifacts": diagnostic_artifacts,
        "source_create_audit": {
            "status": audit_result.get("status") or observe_result.get("status"),
            "passed": audit_result.get("passed") if audit_result else observe_result.get("passed"),
            "needs_post_fix": bool(audit_result.get("needs_post_fix") or observe_result.get("needs_post_fix")),
            "failures": audit_result.get("failures", observe_result.get("failures", [])),
        },
        "requires_user_confirmation": True,
        "auto_execute": False,
        "payload": input_payload,
    }


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
    if not isinstance(data, dict):
        raise TypeError("stdin payload 必须是 JSON object")
    return data


def unwrap_summary_payload(data: dict[str, Any]) -> dict[str, Any]:
    wrapped = data.get("lgwf_wf_create.summary_result")
    if isinstance(wrapped, dict):
        return wrapped
    wrapped = data.get("summary_result")
    if isinstance(wrapped, dict):
        return wrapped
    return data


def load_summary_fallback(work_dir: Path) -> dict[str, Any]:
    path = work_dir / ".lgwf" / "create_result_summary.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(".lgwf/create_result_summary.json 必须是 JSON object")
    return data


def main() -> None:
    summary = unwrap_summary_payload(read_stdin_payload())
    if not str(summary.get("target_package_root", "")).strip():
        summary = load_summary_fallback(Path.cwd())
    if not str(summary.get("target_package_root", "")).strip():
        raise ValueError(
            "summary_result 缺少 target_package_root，且 .lgwf/create_result_summary.json 不存在或不包含该字段"
        )
    payload = build_handoff_payload(summary, Path.cwd())
    print(json.dumps({"lgwf_wf_create.post_fix_handoff_payload": payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
