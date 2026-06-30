from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import output_state


def main() -> None:
    output_state({"prompt_upgrade_confirmation_finished": True})


if __name__ == "__main__":
    main()
