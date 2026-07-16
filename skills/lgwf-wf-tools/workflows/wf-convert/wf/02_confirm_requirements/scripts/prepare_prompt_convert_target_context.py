from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def read_input_payload(root: Path) -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if raw:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    input_state = root / ".lgwf" / "input_state.json"
    if input_state.is_file():
        data = json.loads(input_state.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    return {}


def normalize_target(payload: dict[str, Any]) -> dict[str, Any]:
    target = payload.get("prompt_convert_target")
    if isinstance(target, dict):
        return target
    request = payload.get("request")
    if isinstance(request, dict):
        return {
            "target_dir": request.get("target_dir", ""),
            "entry_files": request.get("entry_files", []),
            "target_workflow_name": request.get("target_workflow_name", ""),
            "target_package_root": request.get("target_package_root", ""),
            "constraints": request.get("constraints", []),
        }
    return {
        "target_dir": "",
        "entry_files": [],
        "target_workflow_name": "",
        "target_package_root": "",
        "constraints": [],
    }


def build_context(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "确认 prompt workflow 转换目标",
        "review_node": "collect_prompt_workflow_target",
        "approval_target": "prompt_convert_target",
        "approve_writes": ".lgwf/prompt_convert_target.json",
        "persist_path": ".lgwf/prompt_convert_target_approval.json",
        "allowed_decisions": ["approve", "revise", "reject"],
        "proposal": target,
        "required_fields": ["target_dir"],
        "optional_fields": ["entry_files", "target_workflow_name", "target_package_root", "constraints"],
    }


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    target = normalize_target(read_input_payload(root))
    lgwf_dir.mkdir(parents=True, exist_ok=True)
    (lgwf_dir / "prompt_convert_target_proposal.json").write_text(
        json.dumps(target, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context = build_context(target)
    print(
        json.dumps(
            {
                "lgwf_wf_convert.prompt_convert_target_context": context,
                "lgwf_wf_convert.prepare_prompt_convert_target_context_result": {
                    "proposal_path": ".lgwf/prompt_convert_target_proposal.json",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
