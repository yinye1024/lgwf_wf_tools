from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STATE_KEY = "lgwf_wf_create_fast.main_agent_handoff_payload"
INTERNAL_ARTIFACTS = {
    "requirements": ".lgwf/create_requirements.json",
    "business_flow": ".lgwf/business_flow.json",
    "scaffold_package_result": ".lgwf/scaffold_package_result.json",
    "materialize_scaffold_result": ".lgwf/materialize_scaffold_result.json",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def read_required_json(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    data = read_json(path)
    if not data:
        raise ValueError(f"{relative_path} 不存在或为空，无法生成 main agent handoff")
    return data


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def quote_command_arg(path: Path) -> str:
    return '"' + str(path).replace('"', '\\"') + '"'


def unwrap_confirmed(data: dict[str, Any]) -> dict[str, Any]:
    confirmed = data.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else data


def unwrap_scaffold_plan(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("scaffold_plan"), dict):
        return data["scaffold_plan"]
    for key in (
        "lgwf_wf_create_fast.scaffold_package_result",
        "scaffold_package_result",
    ):
        wrapped = data.get(key)
        if isinstance(wrapped, dict) and isinstance(wrapped.get("scaffold_plan"), dict):
            return wrapped["scaffold_plan"]
    raise ValueError(".lgwf/scaffold_package_result.json 缺少 scaffold_plan")


def build_handoff_payload(root: Path) -> dict[str, Any]:
    artifacts = {
        name: read_required_json(root, relative_path)
        for name, relative_path in INTERNAL_ARTIFACTS.items()
    }
    requirements = unwrap_confirmed(artifacts["requirements"])
    business_flow = unwrap_confirmed(artifacts["business_flow"])
    scaffold_plan = unwrap_scaffold_plan(artifacts["scaffold_package_result"])
    materialize_result = artifacts["materialize_scaffold_result"]
    target_package_root = str(materialize_result.get("target_package_root", "")).strip()
    target_package_abs = str(materialize_result.get("target_package_abs", "")).strip()
    if not target_package_root:
        raise ValueError("materialize_scaffold_result 缺少 target_package_root")
    if not target_package_abs:
        raise ValueError("materialize_scaffold_result 缺少 target_package_abs")

    validation_commands = materialize_result.get("validation_commands")
    target_abs_path = Path(target_package_abs)
    if not isinstance(validation_commands, list):
        validation_commands = [
            "python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py "
            f"audit {quote_command_arg(target_abs_path / 'wf' / 'workflow.lgwf')}",
            f"python -m unittest discover {quote_command_arg(target_abs_path / 'tests')}",
        ]
    validation_command_list = [str(item) for item in validation_commands if isinstance(item, str)]
    created_files = [str(item) for item in materialize_result.get("created_files", []) if isinstance(item, str)]
    skipped_existing_files = [
        str(item) for item in materialize_result.get("skipped_existing_files", []) if isinstance(item, str)
    ]
    workflow_name = (
        str(materialize_result.get("workflow_name") or scaffold_plan.get("workflow_name") or requirements.get("workflow_name") or "")
        .strip()
    )
    package_profile = str(scaffold_plan.get("package_profile") or requirements.get("package_profile") or "").strip()

    return {
        "handoff_schema_version": 5,
        "workflow_id": "wf-create-fast",
        "next_action": "main_agent_authoring",
        "agent_instruction": "handle_main_agent_authoring",
        "handoff_mode": "confirmed_artifacts_and_target_package",
        "execution_mode": "plan_then_execute",
        "handoff_status": "ready_for_main_agent",
        "handoff_ack_required": True,
        "required_context": [
            "confirmed_requirements",
            "confirmed_business_flow",
            "target_package",
            "execution_contract",
        ],
        "confirmed_requirements": INTERNAL_ARTIFACTS["requirements"],
        "confirmed_business_flow": INTERNAL_ARTIFACTS["business_flow"],
        "target_package": {
            "workflow_name": workflow_name,
            "package_profile": package_profile,
            "root_input": target_package_root,
            "root_abs": target_package_abs,
            "workflow_lgwf": str(target_abs_path / "wf" / "workflow.lgwf"),
            "work_dir": str(target_abs_path / "ws"),
            "tests_dir": str(target_abs_path / "tests"),
            "edit_dirs": [target_package_abs],
            "validation_commands": validation_command_list,
            "materialization": {
                "status": str(materialize_result.get("status", "")).strip(),
                "created_file_count": len(created_files),
                "created_files": created_files,
                "skipped_existing_file_count": len(skipped_existing_files),
                "skipped_existing_files": skipped_existing_files,
            },
        },
        "execution_contract": {
            "plan_required_before_target_edits": True,
            "plan_mechanism": "main_agent_plan_capability",
            "execution_order": [
                "ack_handoff",
                "read_confirmed_context",
                "inspect_target_package_read_only",
                "create_execution_plan",
                "execute_plan_and_track_progress",
                "run_validation_commands",
                "report_result",
            ],
            "minimum_plan_steps": [
                "inspect_confirmed_context_and_scaffold",
                "implement_target_package",
                "run_validation_commands",
            ],
            "progress_policy": (
                "按计划逐项执行并更新状态；如需改变实施路径，先更新计划再继续。"
            ),
        },
        "requires_user_confirmation": False,
        "auto_execute_downstream_workflow": False,
    }


def prepare_main_agent_handoff(root: Path) -> dict[str, Any]:
    payload = build_handoff_payload(root)
    write_json(root / ".lgwf" / "main_agent_authoring_handoff.json", payload)
    return payload


def main() -> None:
    payload = prepare_main_agent_handoff(Path.cwd())
    print(json.dumps({STATE_KEY: payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
