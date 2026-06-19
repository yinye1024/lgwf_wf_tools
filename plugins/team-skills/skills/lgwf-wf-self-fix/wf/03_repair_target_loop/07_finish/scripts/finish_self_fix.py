from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, load_self_fix_target, output_state


def main() -> None:
    target = load_self_fix_target()
    success = target.get("last_status") == "succeeded"
    append_history({"event": "repair_loop_finished", "success": success})
    output_state({"repair_loop_finished": True, "success": success})


if __name__ == "__main__":
    main()
