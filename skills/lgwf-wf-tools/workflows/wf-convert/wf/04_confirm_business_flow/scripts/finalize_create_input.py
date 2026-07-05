from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    proposal_path = lgwf_dir / "wf_create_input_proposal.json"
    confirmed_path = lgwf_dir / "wf_create_input.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8-sig"))
    confirmed_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "decision": "approve",
        "proposal_path": ".lgwf/wf_create_input_proposal.json",
        "confirmed_path": ".lgwf/wf_create_input.json",
    }
    print(json.dumps({"lgwf_wf_convert.finalize_create_input_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

