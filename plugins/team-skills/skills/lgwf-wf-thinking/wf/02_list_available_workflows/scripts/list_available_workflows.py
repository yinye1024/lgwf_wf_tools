from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def find_registry(start: Path) -> Path | None:
    for parent in [start, *start.parents]:
        direct = parent / "registry.json"
        if direct.exists() and parent.name == "lgwf-wf-tools":
            return direct
        sibling = parent / "plugins" / "team-skills" / "skills" / "lgwf-wf-tools" / "registry.json"
        if sibling.exists():
            return sibling
        near_skill = parent.parent / "lgwf-wf-tools" / "registry.json"
        if near_skill.exists():
            return near_skill
    return None


def normalize_registry(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = raw.get("workflows") or raw.get("items") or []
    else:
        items = []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": item.get("id") or item.get("name") or item.get("workflow_id"),
                "name": item.get("name") or item.get("id") or item.get("workflow_id"),
                "description": item.get("description", ""),
                "path": item.get("path") or item.get("workflow") or item.get("workflow_path", ""),
                "tags": item.get("tags", []),
                "inputs": item.get("inputs", {}),
            }
        )
    return normalized


def main() -> None:
    cwd = Path.cwd()
    lgwf_dir = cwd / ".lgwf"
    lgwf_dir.mkdir(parents=True, exist_ok=True)

    registry_path = find_registry(cwd)
    if registry_path is None:
        result = {
            "registry_found": False,
            "registry_path": None,
            "workflows": [],
            "warnings": ["未找到 lgwf-wf-tools/registry.json。"],
        }
    else:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        result = {
            "registry_found": True,
            "registry_path": str(registry_path),
            "workflows": normalize_registry(raw),
            "warnings": [],
        }
    (lgwf_dir / "available_workflows.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_wf_thinking.available_workflows": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
