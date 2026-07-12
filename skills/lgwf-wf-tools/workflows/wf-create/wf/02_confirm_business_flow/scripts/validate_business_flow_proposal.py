"""校验业务流转 proposal 是否可进入 REVIEW。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from proposal_quality_gate import run_quality_gate


def main() -> None:
    result = run_quality_gate(
        Path.cwd(),
        stage="business_flow",
        proposal_file="business_flow_proposal.json",
        gate_file="business_flow_proposal_quality_gate.json",
        input_files=["create_requirements.json", "create_requirements_proposal.json"],
    )
    print(
        json.dumps(
            {"lgwf_wf_create.business_flow_proposal_quality_gate": result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
