from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, load_self_fix_target, output_state


def choose_route(target: dict) -> str:
    status = target.get("last_status")
    if status == "waiting_approval":
        return "approval"
    if status == "succeeded":
        return "finish"
    if status == "failed":
        attempt = int(target.get("current_attempt", 0))
        max_attempts = int(target.get("max_attempts", 5))
        if attempt >= max_attempts:
            return "finish"
        return "fix"
    if status == "running":
        return "observe"
    return "fix"


def main() -> None:
    target = load_self_fix_target()
    route = choose_route(target)
    append_history({"event": "route_after_observe", "route": route, "status": target.get("last_status")})
    output_state({"next_action": route}, next_key=route)


if __name__ == "__main__":
    main()
