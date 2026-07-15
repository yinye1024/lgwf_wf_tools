"""将 raw intent 的 revise 决策写回 canonical proposal。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import write_revised_proposal
from prepare_confirmation import build_confirmation_context


APPROVAL_FILE = "raw_intent_approval.json"
PROPOSAL_FILE = "raw_intent_request_proposal.json"


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    result = write_revised_proposal(
        lgwf_dir=lgwf_dir,
        approval_file=APPROVAL_FILE,
        approval_key="raw_intent_approval",
        proposal_file=PROPOSAL_FILE,
    )
    context = build_confirmation_context(result["proposal"])
    print(
        json.dumps(
            {
                "lgwf_wf_create.raw_intent_revision_result": result,
                "lgwf_wf_create.raw_intent_request_proposal": result["proposal"],
                "lgwf_wf_create.raw_intent_confirmation_context": context,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
