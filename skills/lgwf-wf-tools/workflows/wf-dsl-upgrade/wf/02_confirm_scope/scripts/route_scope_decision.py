from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from dsl_upgrade_common import load_json


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _decision_from(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return str(value.get("decision", "")).strip().lower()


def choose_scope_route(root: Path, approval_result: dict[str, Any] | None = None) -> str:
    approval = load_json(root / ".lgwf" / "scope_approval.json", {})
    validation = load_json(root / ".lgwf" / "target_scope_validation.json", {})
    manifest = load_json(root / ".lgwf" / "target_manifest.json", {})
    decision = _decision_from(approval_result) or _decision_from(approval)
    target_count = len(manifest.get("authorized_targets", []) if isinstance(manifest, dict) else [])
    validation_passed = bool(validation.get("passed")) if isinstance(validation, dict) else False
    if decision == "approve" and validation_passed and target_count > 0:
        route = "run"
    else:
        route = "summary"
    return route


def main() -> None:
    route = choose_scope_route(Path.cwd(), _read_stdin_json())
    print(json.dumps({"wf_dsl_upgrade.scope_route": route}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
