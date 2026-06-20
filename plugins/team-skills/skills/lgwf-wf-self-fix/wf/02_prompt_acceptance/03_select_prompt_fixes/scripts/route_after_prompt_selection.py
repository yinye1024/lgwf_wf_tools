from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import lgwf_dir, output_state, read_json
from validate_prompt_fix_selection import choose_route


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    audit = read_json(root / "audit.json", {})
    selection = read_json(root / "fix_selection.json", {})
    if not isinstance(audit, dict):
        audit = {}
    if not isinstance(selection, dict):
        selection = {}
    route = choose_route(selection, audit)
    output_state({"prompt_selection_route": route}, next_key=route, route_node="route_after_prompt_selection")


if __name__ == "__main__":
    main()
