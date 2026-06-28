"""固化已确认的需求方案。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.confirmation_io import load_json, normalize_relative_path, require_approve, unwrap_approval, write_json


APPROVAL_FILE = "create_requirements_approval.json"
REVISION_APPROVAL_FILE = "create_requirements_revision_approval.json"
OUTPUT_FILE = "create_requirements.json"


def output_artifact_name() -> str:
    return OUTPUT_FILE


def write_confirmed_artifact(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    lgwf_dir.mkdir(parents=True, exist_ok=True)
    source_file = APPROVAL_FILE
    revision_approval = load_json(lgwf_dir / REVISION_APPROVAL_FILE)
    approval = unwrap_approval(revision_approval, "create_requirements_revision_approval") if revision_approval else {}
    if approval:
        source_file = REVISION_APPROVAL_FILE
    else:
        approval = unwrap_approval(load_json(lgwf_dir / APPROVAL_FILE), "create_requirements_approval")
    require_approve(approval)
    confirmed_value = approval.get("confirmed")
    confirmed_payload = confirmed_value if isinstance(confirmed_value, dict) else {
        key: value for key, value in approval.items() if key != "decision"
    }
    target_root = confirmed_payload.get("target_package_root")
    if isinstance(target_root, str) and target_root.strip():
        confirmed_payload["target_package_root"] = normalize_relative_path(target_root, "target_package_root")
    confirmed = {
        "artifact_kind": "create_requirements",
        "artifact_path": f".lgwf/{OUTPUT_FILE}",
        "source_approval_file": f".lgwf/{source_file}",
        "decision": "approve",
        "confirmed": confirmed_payload,
        "approval": approval,
    }
    write_json(lgwf_dir / OUTPUT_FILE, confirmed)
    return {
        "lgwf_wf_create.apply_requirements_result": confirmed,
        "lgwf_wf_create.create_requirements": confirmed,
    }


def main() -> None:
    print(json.dumps(write_confirmed_artifact(Path.cwd()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
