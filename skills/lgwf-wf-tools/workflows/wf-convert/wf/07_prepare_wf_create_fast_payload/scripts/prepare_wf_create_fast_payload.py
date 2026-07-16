from __future__ import annotations

import json
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


DOWNSTREAM_WORKFLOW_ID = "wf-create-fast"
DOWNSTREAM_WORKFLOW_LGWF = "workflows/wf-create-fast/wf/workflow.lgwf"
DOWNSTREAM_WORK_DIR = "workflows/wf-create-fast/ws"
DOWNSTREAM_TARGET_FILE = ".lgwf/wf_create_fast_handoff.json"
DOWNSTREAM_LAUNCH_INPUT_FILE = ".lgwf/wf_create_fast_launch_input.json"


def normalize_package_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    if "://" in cleaned:
        raise ValueError(f"{field_name} 禁止 URL 路径")
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if ":" in cleaned:
        candidate = PureWindowsPath(cleaned)
        if not candidate.is_absolute():
            raise ValueError(f"{field_name} 盘符路径必须是绝对路径")
        parts = candidate.parts
        normalized = str(candidate)
    else:
        candidate = PurePosixPath(cleaned.replace("\\", "/"))
        parts = candidate.parts
        normalized = candidate.as_posix().rstrip("/")
    if any(part == ".." for part in parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in parts):
        raise ValueError(f"{field_name} 禁止写入 `.lgwf`")
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def build_payload(
    *,
    confirmed_input: dict[str, Any],
    package_profile: str = "internal_workflow_package",
) -> dict[str, Any]:
    target_package_root = normalize_package_path(
        str(confirmed_input.get("target_package_root", "")),
        "target_package_root",
    )
    workflow_name = str(confirmed_input.get("workflow_name", "")).strip() or "converted-workflow"
    raw_intent = str(confirmed_input.get("raw_intent", "")).strip()
    if not raw_intent:
        raw_intent = f"基于现有 prompt workflow 创建 LGWF workflow：{workflow_name}"
    payload = {
        "input_mode": "converted_contract",
        "workflow_name": workflow_name,
        "target_package_root": target_package_root,
        "package_profile": package_profile,
        "raw_intent": raw_intent,
        "source_business_contract": confirmed_input.get("source_business_contract", {}),
        "conversion_mapping": confirmed_input.get("conversion_mapping", []),
        "prompt_workflow_context": {
            "stages": confirmed_input.get("stages", []),
            "prompt_contracts": confirmed_input.get("prompt_contracts", []),
            "prompt_execution_mechanics": confirmed_input.get("prompt_execution_mechanics", []),
            "presentation_constraints": confirmed_input.get("presentation_constraints", []),
            "discarded_prompt_techniques": confirmed_input.get("discarded_prompt_techniques", []),
            "parity_requirements": confirmed_input.get("parity_requirements", []),
            "assumptions": confirmed_input.get("assumptions", []),
            "out_of_scope": confirmed_input.get("out_of_scope", []),
        },
    }
    return payload


def build_wf_create_fast_target(payload: dict[str, Any]) -> dict[str, Any]:
    raw_intent = str(payload.get("raw_intent", "")).strip()
    target: dict[str, Any] = {
        "input_mode": "converted_contract",
        "workflow_name": str(payload.get("workflow_name", "")).strip(),
        "target_package_root": str(payload.get("target_package_root", "")).strip(),
        "package_profile": str(payload.get("package_profile", "")).strip(),
        "raw_intent": raw_intent,
    }
    for field in ("source_business_contract", "conversion_mapping", "prompt_workflow_context"):
        value = payload.get(field)
        if value:
            target[field] = value
    return {key: value for key, value in target.items() if value not in ("", [], {})}


def build_wf_create_fast_launch_input(target_file: str) -> dict[str, Any]:
    return {
        "raw_intent": "读取 wf-convert 生成的完整 handoff target file，并据此创建 LGWF workflow。",
        "request": {
            "target_file": target_file,
        },
    }


def quote_command_arg(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def build_handoff_state(
    *,
    target_file: str,
    target_file_for_launch: str,
    launch_input_file: str,
) -> dict[str, Any]:
    launch_input = build_wf_create_fast_launch_input(target_file_for_launch)
    return {
        "workflow_id": DOWNSTREAM_WORKFLOW_ID,
        "next_workflow_id": DOWNSTREAM_WORKFLOW_ID,
        "next_action": "start_workflow",
        "agent_instruction": "handle_handoff",
        "handoff_status": "ready_for_main_agent_ack",
        "handoff_ack_required": True,
        "downstream_workflow_id": DOWNSTREAM_WORKFLOW_ID,
        "downstream_workflow_lgwf": DOWNSTREAM_WORKFLOW_LGWF,
        "downstream_work_dir": DOWNSTREAM_WORK_DIR,
        "workflow_lgwf": DOWNSTREAM_WORKFLOW_LGWF,
        "work_dir": DOWNSTREAM_WORK_DIR,
        "input_json_file": launch_input_file,
        "target_file": target_file,
        "target_file_for_launch": target_file_for_launch,
        "wf_create_fast_launch_input": launch_input,
        "input_mode": "target_file",
        "launch_steps": [
            "主 agent 先提交 handoff ack，记录已接收。",
            "使用 input_json_file 指向的 UTF-8 no BOM JSON 文件启动 wf-create-fast。",
            "target_file 是 wf-create-fast 要读取的创建资料。",
        ],
        "suggested_command": (
            "python skills/lgwf-wf-tools/scripts/run_skill_workflow.py "
            f"--workflow-id {DOWNSTREAM_WORKFLOW_ID} "
            f"--input-json-file {quote_command_arg(launch_input_file)}"
        ),
        "requires_user_confirmation": True,
        "auto_execute_downstream_workflow": False,
    }


def main() -> None:
    from pathlib import Path

    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    confirmed_input_path = lgwf_dir / "wf_create_fast_input.json"
    confirmed_input = json.loads(confirmed_input_path.read_text(encoding="utf-8-sig"))
    payload = build_payload(
        confirmed_input=confirmed_input,
        package_profile=str(confirmed_input.get("package_profile", "internal_workflow_package")),
    )
    wf_create_fast_target = build_wf_create_fast_target(payload)
    wf_create_fast_target_path = lgwf_dir / "wf_create_fast_handoff.json"
    wf_create_fast_target_path.write_text(
        json.dumps(wf_create_fast_target, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    target_file_for_launch = str(wf_create_fast_target_path.resolve())
    launch_input_path = root / DOWNSTREAM_LAUNCH_INPUT_FILE
    launch_input = build_wf_create_fast_launch_input(target_file_for_launch)
    launch_input_path.write_text(
        json.dumps(launch_input, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    handoff_state = build_handoff_state(
        target_file=DOWNSTREAM_TARGET_FILE,
        target_file_for_launch=target_file_for_launch,
        launch_input_file=str(launch_input_path.resolve()),
    )
    print(json.dumps({"lgwf_wf_convert.wf_create_fast_handoff_payload": handoff_state}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
