from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import finish_decision_only_stage


def main() -> None:
    finish_decision_only_stage("script_flow_e2e", "script_flow_e2e_result", "route_script_flow_e2e")


if __name__ == "__main__":
    main()
