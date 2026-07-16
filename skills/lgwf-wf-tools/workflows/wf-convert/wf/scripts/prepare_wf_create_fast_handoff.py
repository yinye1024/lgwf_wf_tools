from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


STATE_KEY = "lgwf_wf_convert.wf_create_fast_handoff_payload"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return payload


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("wf_create_fast_input 必须是 JSON object")
    return payload


def build_handoff_payload(child_input: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    if not child_input:
        child_input = read_json(lgwf_dir / "wf_create_fast_input_for_wf_create_fast.json")
    convert_payload = read_json(lgwf_dir / "wf_create_fast_payload.json")
    raw_intent = child_input.get("raw_intent")
    if not isinstance(raw_intent, str) or not raw_intent.strip():
        raise ValueError("wf-create-fast handoff 输入缺少非空 raw_intent")

    input_json_file = lgwf_dir / "wf_create_fast_input_for_wf_create_fast.json"
    workflow_lgwf = "workflows/wf-create-fast/wf/workflow.lgwf"
    downstream_work_dir = "workflows/wf-create-fast/ws"
    suggested_command = (
        "python skills/lgwf-wf-tools/scripts/run_skill_workflow.py "
        "--workflow-id wf-create-fast "
        f"--input-json-file {input_json_file.as_posix()}"
    )

    return {
        "workflow_id": "wf-create-fast",
        "next_workflow_id": "wf-create-fast",
        "next_action": "start_workflow",
        "workflow_lgwf": workflow_lgwf,
        "work_dir": downstream_work_dir,
        "downstream_workflow_id": "wf-create-fast",
        "downstream_workflow_lgwf": workflow_lgwf,
        "downstream_work_dir": downstream_work_dir,
        "input_json_file": input_json_file.as_posix(),
        "payload_file": ".lgwf/wf_create_fast_payload.json",
        "source_artifacts": [
            ".lgwf/prompt_convert_target.json",
            ".lgwf/prompt_workflow_inspection.json",
            ".lgwf/wf_create_fast_input.json",
            ".lgwf/wf_create_fast_payload.json",
            ".lgwf/wf_create_fast_input_for_wf_create_fast.json",
        ],
        "wf_create_fast_input": child_input,
        "prompt_convert_payload": convert_payload.get("prompt_convert_payload", {}),
        "main_agent_instruction": (
            "读取 input_json_file 后启动 wf-create-fast 创建工作流；"
            "不要在 wf-convert 内继续实现目标 package；"
            "不要启动 wf-create；不要生成 step_designs.json。"
        ),
        "suggested_command": suggested_command,
        "requires_user_confirmation": False,
        "auto_execute": False,
        "auto_execute_downstream_workflow": False,
    }


def main() -> None:
    work_dir = Path.cwd()
    payload = build_handoff_payload(read_stdin_payload(), work_dir)
    output_path = work_dir / ".lgwf" / "wf_create_fast_handoff.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({STATE_KEY: payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
