from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import finish_or_record_stage_decision


def main() -> None:
    finish_or_record_stage_decision("prompt_fix", "prompt_fix_stage_route", "prompt_fix_stage")


if __name__ == "__main__":
    main()
