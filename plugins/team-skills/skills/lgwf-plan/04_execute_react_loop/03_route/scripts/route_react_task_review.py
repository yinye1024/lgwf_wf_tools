from __future__ import annotations

import json
from pathlib import Path


ROUTE_NODE_ID = "route_react_task_review"
ROUTE_KEY = f"__route__{ROUTE_NODE_ID}"


def main() -> None:
    path = Path.cwd() / ".lgwf" / "react_task_route.json"
    if path.exists():
        route = json.loads(path.read_text(encoding="utf-8-sig"))
    else:
        route = {"route": "all_done"}
    next_route = route.get("route")
    if not isinstance(next_route, str) or not next_route:
        raise SystemExit("react_task_route.route must be a non-empty string")
    print(
        json.dumps(
            {
                ROUTE_KEY: next_route,
                "lgwf_plan.react_task_route": route,
                "lgwf_plan.next_route": next_route,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

