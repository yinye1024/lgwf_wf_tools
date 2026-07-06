from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"


def _load_contract(relative_path: object) -> dict[str, object]:
    if not isinstance(relative_path, str) or not relative_path:
        return {}
    path = FACADE_ROOT / relative_path
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _required_fields(contract: dict[str, object]) -> list[str]:
    schema = contract.get("input_schema")
    if not isinstance(schema, dict):
        return []
    required = schema.get("required")
    if not isinstance(required, list):
        return []
    return [item for item in required if isinstance(item, str)]


def list_workflows() -> dict[str, Any]:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    workflows = registry.get("workflows", [])
    items = []
    if isinstance(workflows, list):
        for item in workflows:
            if isinstance(item, dict):
                contract = _load_contract(item.get("entry_contract"))
                items.append(
                    {
                        "id": item.get("id", ""),
                        "kind": item.get("kind", "lgwf"),
                        "description": item.get("description", ""),
                        "workflow_lgwf": item.get("workflow_lgwf", ""),
                        "work_dir": item.get("work_dir", ""),
                        "agents_md": item.get("agents_md", ""),
                        "entry": item.get("entry", ""),
                        "entry_contract": item.get("entry_contract", ""),
                        "input_mode": contract.get("input_mode", ""),
                        "auto_human_policy": contract.get("auto_human_policy", ""),
                        "required_fields": _required_fields(contract),
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
