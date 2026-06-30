from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, write_json
from target_repair_loop import load_current_artifact


def main() -> None:
    target = load_self_fix_target()
    attempt = int(target.get("current_attempt", 0))
    root = lgwf_dir()
    apply_result = load_current_artifact(root, "apply", {})
    if not isinstance(apply_result, dict):
        apply_result = {}
    notes = apply_result.get("summary") or apply_result.get("notes") or ""
    event = {"event": "fix_attempt_recorded", "attempt": attempt, "notes": notes}
    append_history(event)
    target["last_status"] = "fixed"
    write_json(root / "self_fix_target.json", target)
    output_state({"target": target, "last_fix_notes": notes, "next_action": "run"})


if __name__ == "__main__":
    main()
