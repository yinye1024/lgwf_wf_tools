from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"


def list_workflows() -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    workflows = registry.get("workflows", [])
    items = []
    if isinstance(workflows, list):
        for item in workflows:
            if isinstance(item, dict):
                items.append(
                    {
                        "id": item.get("id", ""),
                        "kind": item.get("kind", "lgwf"),
                        "description": item.get("description", ""),
                        "workflow_lgwf": item.get("workflow_lgwf", ""),
                        "work_dir": item.get("work_dir", ""),
                        "agents_md": item.get("agents_md", ""),
                        "entry": item.get("entry", ""),
                    }
                )
    return {"facade_root": str(FACADE_ROOT), "workflows": items}


def main() -> None:
    print(json.dumps(list_workflows(), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"list_workflows failed: {exc}", file=sys.stderr)
        raise
