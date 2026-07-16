from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STATE_KEY = "lgwf_wf_create_fast.main_agent_handoff_payload"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_handoff_payload(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    materialize_result = read_json(lgwf_dir / "materialize_scaffold_result.json")
    if not materialize_result:
        raise ValueError(".lgwf/materialize_scaffold_result.json 不存在或为空")
    target_package_root = str(materialize_result.get("target_package_root", "")).strip()
    target_package_abs = str(materialize_result.get("target_package_abs", "")).strip()
    if not target_package_root:
        raise ValueError("materialize_scaffold_result 缺少 target_package_root")
    if not target_package_abs:
        raise ValueError("materialize_scaffold_result 缺少 target_package_abs")

    validation_commands = materialize_result.get("validation_commands")
    if not isinstance(validation_commands, list):
        validation_commands = [
            f"python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit --workflow-lgwf {target_package_root}/wf/workflow.lgwf",
            f"python -m unittest discover {target_package_root}/tests",
        ]

    return {
        "workflow_id": "wf-create-fast",
        "next_action": "main_agent_authoring",
        "target_package_root": target_package_root,
        "target_package_abs": target_package_abs,
        "target_workflow_lgwf": f"{target_package_root}/wf/workflow.lgwf",
        "edit_dirs": [target_package_root],
        "source_artifacts": [
            ".lgwf/create_requirements.json",
            ".lgwf/business_flow.json",
            ".lgwf/scaffold_package_result.json",
            ".lgwf/materialize_scaffold_result.json",
        ],
        "main_agent_instruction": (
            "基于已确认需求、业务流和已落盘 scaffold，直接完善目标 workflow package；"
            "不要生成 step_designs.json；不要进入 wf-create 的 03/04 实现链路。"
        ),
        "validation_commands": [str(item) for item in validation_commands if isinstance(item, str)],
        "requires_user_confirmation": False,
        "auto_execute_downstream_workflow": False,
        "materialize_status": materialize_result.get("status", ""),
        "skipped_existing_files": materialize_result.get("skipped_existing_files", []),
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
