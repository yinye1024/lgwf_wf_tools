from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    request = json.loads(Path(".lgwf/e2e_target_request.normalized.json").read_text(encoding="utf-8-sig"))
    selected = set(request.get("selected_test_types") or [])
    next_route = "run" if "real_positive" in selected else "skip"
    print(
        json.dumps(
            {
                "__route__route_real_positive_selection": next_route,
                "next": next_route,
                "selected": next_route == "run",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
