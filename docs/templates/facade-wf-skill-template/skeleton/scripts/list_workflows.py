from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_contract(relative_path: object) -> dict[str, Any]:
    if not isinstance(relative_path, str) or not relative_path:
        return {}
    path = FACADE_ROOT / relative_path
    if not path.is_file():
        return {}
    data = _load_json(path)
    return data if isinstance(data, dict) else {}


def _required_fields(contract: dict[str, Any]) -> list[str]:
    schema = contract.get("input_schema")
    if not isinstance(schema, dict):
        return []
    required = schema.get("required")
    if not isinstance(required, list):
        return []
    return [item for item in required if isinstance(item, str)]


def list_workflows() -> dict[str, Any]:
    registry = _load_json(REGISTRY_PATH)
    workflows = registry.get("workflows", []) if isinstance(registry, dict) else []
    items: list[dict[str, Any]] = []
    if isinstance(workflows, list):
        for item in workflows:
            if not isinstance(item, dict):
                continue
            contract = _load_contract(item.get("entry_contract"))
            items.append(
                {
                    "id": item.get("id", ""),
                    "kind": item.get("kind", "lgwf"),
                    "description": item.get("description", ""),
                    "workflow_lgwf": item.get("workflow_lgwf", ""),
                    "work_dir": item.get("work_dir", ""),
                    "entry": item.get("entry", ""),
                    "agents_md": item.get("agents_md", ""),
                    "entry_contract": item.get("entry_contract", ""),
                    "input_mode": contract.get("input_mode", ""),
                    "auto_human_policy": contract.get("auto_human_policy", ""),
                    "required_fields": _required_fields(contract),
                }
            )
    return {"facade_root": str(FACADE_ROOT), "workflows": items}


def main() -> None:
    print(json.dumps(list_workflows(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"list_workflows failed: {exc}", file=sys.stderr)
        raise
