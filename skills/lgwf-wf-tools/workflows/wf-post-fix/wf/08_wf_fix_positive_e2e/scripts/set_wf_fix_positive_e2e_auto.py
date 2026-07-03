from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import enable_auto_for_stage, load_decisions, output_state


def main() -> None:
    decision = enable_auto_for_stage("wf_fix_positive_e2e")
    output_state({"wf_fix_positive_e2e_decision": decision, "post_fix_decisions": load_decisions()})


if __name__ == "__main__":
    main()
