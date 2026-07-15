"""根据初版步骤设计 observation 决定是否进入 repair ReAct。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROUTE_NODE_ID = "route_step_design_repair_entry"
ROUTE_KEY = f"__route__{ROUTE_NODE_ID}"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    observation = read_json(Path.cwd() / ".lgwf" / "step_design_observation.json")
    route = "pass" if observation.get("passed") is True else "repair"
    print(
        json.dumps(
            {
                ROUTE_KEY: route,
                "lgwf_wf_create.step_design_repair_entry_route": {
                    "route": route,
                    "passed": observation.get("passed") is True,
                    "observation_file": ".lgwf/step_design_observation.json",
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
