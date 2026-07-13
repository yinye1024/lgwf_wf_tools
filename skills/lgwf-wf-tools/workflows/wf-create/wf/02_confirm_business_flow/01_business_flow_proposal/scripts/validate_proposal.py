"""校验业务流转 proposal 是否可进入 REVIEW。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from proposal_quality_gate import evaluate_quality_gate, write_json


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    result = evaluate_quality_gate(
        lgwf_dir,
        stage="business_flow",
        proposal_path=lgwf_dir / "business_flow_proposal.json",
        input_paths=[lgwf_dir / "create_requirements.json", lgwf_dir / "create_requirements_proposal.json"],
    )
    write_json(lgwf_dir / "business_flow_proposal_quality_gate.json", result)
    print(
        json.dumps(
            {"lgwf_wf_create.business_flow_proposal_quality_gate": result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
