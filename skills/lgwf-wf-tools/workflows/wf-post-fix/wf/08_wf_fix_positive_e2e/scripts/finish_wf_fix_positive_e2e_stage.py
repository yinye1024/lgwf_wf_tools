from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import finish_decision_only_stage


def main() -> None:
    finish_decision_only_stage("wf_fix_positive_e2e", "wf_fix_positive_e2e_result", "route_wf_fix_positive")


if __name__ == "__main__":
    main()
