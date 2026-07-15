"""固化已确认的需求方案。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import confirmed_from_proposal, load_json, normalize_relative_path, unwrap_approval, write_json


APPROVAL_FILE = "create_requirements_approval.json"
PROPOSAL_FILE = "create_requirements_proposal.json"
OUTPUT_FILE = "create_requirements.json"


def output_artifact_name() -> str:
    return OUTPUT_FILE


def resolve_confirmed_payload(lgwf_dir: Path, approval: dict[str, Any]) -> dict[str, Any]:
    return confirmed_from_proposal(lgwf_dir, approval, PROPOSAL_FILE)


def write_confirmed_artifact(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    lgwf_dir.mkdir(parents=True, exist_ok=True)
    source_file = APPROVAL_FILE
    approval = unwrap_approval(load_json(lgwf_dir / APPROVAL_FILE), "create_requirements_approval")
    confirmed_payload = resolve_confirmed_payload(lgwf_dir, approval)
    target_root = confirmed_payload.get("target_package_root")
    if isinstance(target_root, str) and target_root.strip():
        confirmed_payload["target_package_root"] = normalize_relative_path(target_root, "target_package_root")
    confirmed = {
        "artifact_kind": "create_requirements",
        "artifact_path": f".lgwf/{OUTPUT_FILE}",
        "source_proposal_file": f".lgwf/{PROPOSAL_FILE}",
        "source_approval_file": f".lgwf/{source_file}",
        "decision": "approve",
        "confirmed": confirmed_payload,
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
