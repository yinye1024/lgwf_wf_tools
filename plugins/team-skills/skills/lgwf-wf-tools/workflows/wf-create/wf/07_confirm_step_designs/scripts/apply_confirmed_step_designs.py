"""固化已确认的步骤设计。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import load_json, normalize_relative_path, require_approve, unwrap_approval, write_json


APPROVAL_FILE = "step_design_confirmation_record.json"
REVISION_APPROVAL_FILE = "step_design_revision_approval.json"
OUTPUT_FILE = "step_designs.json"


def output_artifact_name() -> str:
    return OUTPUT_FILE


def write_confirmed_artifact(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    lgwf_dir.mkdir(parents=True, exist_ok=True)
    source_file = APPROVAL_FILE
    revision_approval = load_json(lgwf_dir / REVISION_APPROVAL_FILE)
    approval = unwrap_approval(revision_approval, "step_design_revision_approval") if revision_approval else {}
    if approval:
        source_file = REVISION_APPROVAL_FILE
    else:
        approval = unwrap_approval(load_json(lgwf_dir / APPROVAL_FILE), "step_design_confirmation_record")
    require_approve(approval)
    confirmed_value = approval.get("confirmed")
    confirmed_payload = confirmed_value if isinstance(confirmed_value, dict) else {
        key: value for key, value in approval.items() if key != "decision"
    }
    for key in ("approved_step_designs_path", "step_designs_path"):
        if isinstance(confirmed_payload.get(key), str) and confirmed_payload[key].strip():
            confirmed_payload[key] = normalize_relative_path(confirmed_payload[key], key)
    confirmed = {
        "artifact_kind": "step_designs",
        "artifact_path": f".lgwf/{OUTPUT_FILE}",
        "source_approval_file": f".lgwf/{source_file}",
        "decision": "approve",
        "confirmed": confirmed_payload,
        "approval": approval,
    }
    write_json(lgwf_dir / OUTPUT_FILE, confirmed)
    return {
        "lgwf_wf_create.apply_step_designs_result": confirmed,
        "lgwf_wf_create.step_designs": confirmed,
    }


def main() -> None:
    print(json.dumps(write_confirmed_artifact(Path.cwd()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
