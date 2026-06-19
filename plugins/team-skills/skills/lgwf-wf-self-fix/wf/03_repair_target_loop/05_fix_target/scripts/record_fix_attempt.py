from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, read_text, write_json


def main() -> None:
    target = load_self_fix_target()
    attempt = int(target.get("current_attempt", 0))
    notes = read_text(lgwf_dir() / "target_fix_notes.md", limit=10000)
    event = {"event": "fix_attempt_recorded", "attempt": attempt, "notes": notes}
    append_history(event)
    target["last_status"] = "fixed"
    write_json(lgwf_dir() / "self_fix_target.json", target)
    output_state({"target": target, "last_fix_notes": notes, "next_action": "run"})


if __name__ == "__main__":
    main()
