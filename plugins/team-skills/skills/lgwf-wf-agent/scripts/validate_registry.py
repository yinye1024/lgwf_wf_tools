from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"


def is_safe_relative_path(raw: Any) -> bool:
    if not isinstance(raw, str) or not raw.strip():
        return False
    path = Path(raw)
    return not path.is_absolute() and ".." not in path.parts


def check_workflow_item(item: Any, seen_ids: set[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not isinstance(item, dict):
        return [{"label": "workflow_item_object", "passed": False, "reason": "workflow item must be object"}]

    workflow_id = item.get("id")
    id_valid = isinstance(workflow_id, str) and bool(workflow_id.strip())
    checks.append({"label": "workflow_id_present", "passed": id_valid, "workflow_id": workflow_id})
    if id_valid:
        checks.append({"label": "workflow_id_unique", "passed": workflow_id not in seen_ids, "workflow_id": workflow_id})
        seen_ids.add(workflow_id)

    for key in ("workflow_lgwf", "work_dir", "agents_md"):
        raw_path = item.get(key)
        path_safe = is_safe_relative_path(raw_path)
        checks.append({"label": f"{workflow_id}.{key}.relative_path", "passed": path_safe, "path": raw_path})
        if path_safe:
            full_path = FACADE_ROOT / str(raw_path)
            if key == "work_dir":
                checks.append(
                    {
                        "label": f"{workflow_id}.{key}.parent_exists",
                        "passed": full_path.parent.exists(),
                        "path": str(full_path),
                        "parent": str(full_path.parent),
                    }
                )
            else:
                checks.append({"label": f"{workflow_id}.{key}.exists", "passed": full_path.exists(), "path": str(full_path)})

    workflow_lgwf = item.get("workflow_lgwf")
    work_dir = item.get("work_dir")
    if is_safe_relative_path(workflow_lgwf) and is_safe_relative_path(work_dir):
        workflow_root = (FACADE_ROOT / str(workflow_lgwf)).parent
        work_dir_path = FACADE_ROOT / str(work_dir)
        checks.append(
            {
                "label": f"{workflow_id}.work_dir_not_source_root",
                "passed": workflow_root.resolve() != work_dir_path.resolve(),
                "workflow_root": str(workflow_root),
                "work_dir": str(work_dir_path),
            }
        )

    return checks


def run_validation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    registry_exists = REGISTRY_PATH.is_file()
    checks.append({"label": "registry_json_exists", "passed": registry_exists, "path": str(REGISTRY_PATH)})
    if not registry_exists:
        return {"passed": False, "registry_path": str(REGISTRY_PATH), "checks": checks}

    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    workflows = data.get("workflows") if isinstance(data, dict) else None
    checks.append({"label": "workflows_list", "passed": isinstance(workflows, list)})
    seen_ids: set[str] = set()
    if isinstance(workflows, list):
        for item in workflows:
            checks.extend(check_workflow_item(item, seen_ids))

    nested_skill_files = [
        str(path.relative_to(FACADE_ROOT))
        for path in (FACADE_ROOT / "workflows").rglob("SKILL.md")
    ]
    checks.append(
        {
            "label": "internal_workflows_no_skill_md",
            "passed": not nested_skill_files,
            "matches": nested_skill_files,
        }
    )

    return {
        "passed": all(bool(check.get("passed")) for check in checks),
        "registry_path": str(REGISTRY_PATH),
        "checks": checks,
    }


def main() -> None:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validate_registry failed: {exc}", file=sys.stderr)
        raise
