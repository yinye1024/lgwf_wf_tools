from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path.cwd() / ".lgwf" / "react_task_route.json"
    if path.exists():
        route = json.loads(path.read_text(encoding="utf-8-sig"))
    else:
        route = {"route": "all_done"}
    print(json.dumps({"lgwf_plan.react_task_route": route, "lgwf_plan.next_route": route.get("route")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

