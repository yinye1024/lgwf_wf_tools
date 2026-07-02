from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


def normalize_package_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute():
        raise ValueError(f"{field_name} 禁止绝对路径")
    if ":" in cleaned:
        raise ValueError(f"{field_name} 禁止盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止写入 `.lgwf`")
    return candidate.as_posix().strip("/")


def build_payload(
    *,
    confirmed_input: dict[str, Any],
    approval: dict[str, Any],
    package_profile: str = "internal_workflow_package",
) -> dict[str, Any]:
    decision = str(approval.get("decision", approval.get("approval", ""))).lower()
    if decision and decision != "approve":
        raise ValueError("只有 approve 后才能生成 wf-create payload")
    target_package_root = normalize_package_path(
        str(confirmed_input.get("target_package_root", "")),
        "target_package_root",
    )
    workflow_name = str(confirmed_input.get("workflow_name", "")).strip() or "converted-workflow"
    raw_intent = str(confirmed_input.get("raw_intent", "")).strip()
    if not raw_intent:
        raw_intent = f"基于现有 prompt workflow 创建 LGWF workflow：{workflow_name}"
    payload = {
        "workflow_name": workflow_name,
        "target_package_root": target_package_root,
        "source_root": str(confirmed_input.get("source_root", "")),
        "package_profile": package_profile,
        "raw_intent": raw_intent,
        "prompt_workflow_context": {
            "stages": confirmed_input.get("stages", []),
            "prompt_contracts": confirmed_input.get("prompt_contracts", []),
            "assumptions": confirmed_input.get("assumptions", []),
            "out_of_scope": confirmed_input.get("out_of_scope", []),
        },
    }
    return payload


def main() -> None:
    from pathlib import Path

    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    approval_path = lgwf_dir / "wf_create_input_approval.json"
    proposal_path = lgwf_dir / "wf_create_input_proposal.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    value = approval.get("value", approval)
    confirmed_input = value.get("confirmed") if isinstance(value, dict) else None
    if not isinstance(confirmed_input, dict):
        confirmed_input = json.loads(proposal_path.read_text(encoding="utf-8-sig"))
    payload = build_payload(
        confirmed_input=confirmed_input,
        approval=value if isinstance(value, dict) else approval,
        package_profile=str(confirmed_input.get("package_profile", "internal_workflow_package")),
    )
    wf_create_input_path = lgwf_dir / "wf_create_input_for_wf_create.json"
    wf_create_input = {"raw_intent": payload["raw_intent"]}
    wf_create_input_path.write_text(json.dumps(wf_create_input, ensure_ascii=False, indent=2), encoding="utf-8")
    output = {"prompt_convert_payload": payload, "wf_create_payload": wf_create_input}
    output_path = lgwf_dir / "wf_create_payload.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"lgwf_wf_convert.wf_create_payload": output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
