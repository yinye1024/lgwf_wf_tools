"""按 raw intent review 决策固化候选对象。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import approval_decision, require_approve


APPROVAL_FILE = "raw_intent_approval.json"
PROPOSAL_FILE = "raw_intent_request_proposal.json"
OUTPUT_FILE = "raw_intent_request.json"


def load_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_stdin_context() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    return payload if isinstance(payload, dict) else {}


def _approval_route(approval: dict[str, Any]) -> str:
    return approval_decision(approval)


def _proposal_from_context(context: dict[str, Any]) -> dict[str, Any]:
    proposal = context.get("proposal")
    return proposal if isinstance(proposal, dict) else {}


def confirmed_raw_intent(lgwf_dir: Path, context: dict[str, Any] | None = None) -> dict[str, Any]:
    approval = load_json(lgwf_dir / APPROVAL_FILE)
    if not isinstance(approval, dict):
        raise ValueError(".lgwf/raw_intent_approval.json 必须是 JSON object")
    require_approve(approval)
    proposal = _proposal_from_context(context or {}) or load_json(lgwf_dir / PROPOSAL_FILE)
    if not isinstance(proposal, dict) or not proposal:
        raise ValueError("approve 需要已存在的非空 raw_intent_request_proposal.json")
    return proposal


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    confirmed = confirmed_raw_intent(lgwf_dir, read_stdin_context())
    write_json(lgwf_dir / OUTPUT_FILE, confirmed)
    print(
        json.dumps(
            {
                "lgwf_wf_create_fast.raw_intent_request": confirmed,
                "lgwf_wf_create_fast.raw_intent_apply_result": {
                    "artifact_path": f".lgwf/{OUTPUT_FILE}",
                    "source_proposal_file": f".lgwf/{PROPOSAL_FILE}",
                    "source_approval_file": f".lgwf/{APPROVAL_FILE}",
                    "decision": _approval_route(load_json(lgwf_dir / APPROVAL_FILE)),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
