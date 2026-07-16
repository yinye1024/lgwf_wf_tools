"""组合 proposal 与非阻塞 Observe issues，供人工确认节点消费。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def build_confirmation_context(
    proposal: dict[str, Any],
    observe: dict[str, Any],
) -> dict[str, Any]:
    issues = observe.get("issues", [])
    if not isinstance(issues, list):
        raise TypeError("observe.issues 必须是数组")
    if observe.get("blocking") is not False:
        raise ValueError("只有 canonical Observe blocking=false 时才能进入人工确认")
    non_blocking_issues = [
        item
        for item in issues
        if isinstance(item, dict) and item.get("blocking") is False
    ]
    return {
        "proposal": proposal,
        "non_blocking_issues": non_blocking_issues,
        "observe_summary": {
            "verdict": observe.get("verdict"),
            "blocking": False,
            "observer_status": observe.get("observer_status", {}),
        },
    }


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    proposal = read_json_object(lgwf_dir / "wf_create_fast_input_proposal.json")
    observe = read_json_object(lgwf_dir / "wf_create_fast_input_observe.json")
    context = build_confirmation_context(proposal, observe)
    output_path = lgwf_dir / "wf_create_fast_input_confirmation_context.json"
    output_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"lgwf_wf_convert.wf_create_fast_input_confirmation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
