from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import read_json, route_for_failure, unique_in_order, write_json


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    results = read_json(lgwf_dir / "verification_results.json")
    routes: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in results.get("commands", []):
        if not isinstance(item, dict):
            continue
        failure_type = item.get("failure_type")
        if not failure_type or failure_type in seen:
            continue
        seen.add(str(failure_type))
        route = route_for_failure(str(failure_type))
        route["check_id"] = item.get("check_id", "")
        routes.append(route)
    for item in results.get("skipped", []):
        if isinstance(item, dict) and "zip" in str(item.get("reason", "")) and "zip_conflict" not in seen:
            seen.add("zip_conflict")
            route = route_for_failure("zip_conflict")
            route["check_id"] = item.get("check_id", "")
            routes.append(route)

    payload = {
        "artifact_kind": "failure_routes",
        "routes": routes,
    }
    write_json(lgwf_dir / "failure_routes.json", payload)
    print(
        json.dumps(
            {"wf_maintenance_gate.failure_routes": payload},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
