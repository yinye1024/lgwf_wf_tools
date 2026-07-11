from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import aggregate_impact, classify_path, read_json, unique_in_order, write_json


def combine_classifications(paths: list[str], workflow_ids: list[str]) -> dict[str, object]:
    items = [classify_path(path, workflow_ids) for path in paths if path]
    if not items:
        return classify_path("", workflow_ids)
    primary = max(items, key=lambda item: int(item.get("priority", 0)))
    return {
        "category": primary["category"],
        "matched_rules": unique_in_order(
            [rule_id for item in items for rule_id in item.get("matched_rules", [])]
        ),
        "priority": primary["priority"],
        "risk": max((str(item.get("risk", "low")) for item in items), key=lambda value: {"low": 1, "medium": 2, "high": 3}[value]),
        "impacted_workflows": unique_in_order(
            [workflow_id for item in items for workflow_id in item.get("impacted_workflows", [])]
        ),
        "recommended_checks": unique_in_order(
            [check for item in items for check in item.get("recommended_checks", [])]
        ),
        "rationale": "；".join(str(item.get("rationale", "")) for item in items if item.get("rationale")),
    }


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    change_context = read_json(lgwf_dir / "change_context.json")
    registry_workflows = change_context.get("registry_workflows", [])
    workflow_ids = [item.get("id", "") for item in registry_workflows if isinstance(item, dict) and item.get("id")]
    files_result: list[dict[str, object]] = []
    for item in change_context.get("files", []):
        if not isinstance(item, dict):
            continue
        paths = [str(item.get("path", ""))]
        old_path = str(item.get("old_path", ""))
        if old_path:
            paths.append(old_path)
        classification = combine_classifications(paths, workflow_ids)
        files_result.append(
            {
                "path": item.get("path", ""),
                "old_path": old_path,
                "change_kind": item.get("change_kind", ""),
                "git_status_code": item.get("git_status_code", ""),
                **classification,
            }
        )

    aggregate = aggregate_impact(files_result)
    impact = {
        "artifact_kind": "impact_classification",
        "files": files_result,
        "categories": aggregate["categories"],
        "impacted_workflows": aggregate["impacted_workflows"],
        "risk": aggregate["risk"],
        "recommended_checks": aggregate["recommended_checks"],
        "ambiguities": aggregate["ambiguities"],
    }
    write_json(lgwf_dir / "impact_classification.json", impact)
    print(
        json.dumps(
            {"wf_maintenance_gate.impact_classification": impact},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
