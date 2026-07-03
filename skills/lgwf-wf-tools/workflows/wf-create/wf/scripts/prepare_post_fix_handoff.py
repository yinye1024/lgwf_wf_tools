from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


WF_POST_FIX_LGWF = "skills/lgwf-wf-tools/workflows/wf-post-fix/wf/workflow.lgwf"
WF_POST_FIX_WORK_DIR = "skills/lgwf-wf-tools/workflows/wf-post-fix/ws"


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


def main() -> None:
    summary = read_stdin_payload()
    payload = build_handoff_payload(summary, Path.cwd())
    print(json.dumps({"lgwf_wf_create.post_fix_handoff_payload": payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
