"""固化已通过 structural gate 的步骤设计。"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import load_json, normalize_relative_path, write_json


PROPOSAL_FILE = "step_designs_proposal.json"
OBSERVATION_FILE = "step_design_observation.json"
OUTPUT_FILE = "step_designs.json"


def output_artifact_name() -> str:
    return OUTPUT_FILE


def stable_json_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def require_current_structural_gate(lgwf_dir: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    observation = load_json(lgwf_dir / OBSERVATION_FILE)
    if observation.get("passed") is not True:
        raise ValueError("步骤设计 structural gate 未通过，不能固化 step_designs.json")
    observed_hash = str(observation.get("proposal_hash", "")).strip()
    current_hash = stable_json_hash(proposal)
    if not observed_hash:
        raise ValueError("步骤设计 observation 缺少 proposal_hash，不能确认 structural gate 覆盖当前 proposal")
    if observed_hash != current_hash:
        raise ValueError("步骤设计 proposal 已变化，必须重新运行 structural gate 后才能固化")
    return observation


def resolve_validated_payload(lgwf_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    proposal = load_json(lgwf_dir / PROPOSAL_FILE)
    if not proposal:
        raise ValueError(f"{PROPOSAL_FILE} 不存在或为空，无法固化 step_designs.json")
    observation = require_current_structural_gate(lgwf_dir, proposal)
    for key in ("approved_step_designs_path", "step_designs_path"):
        if isinstance(proposal.get(key), str) and proposal[key].strip():
            proposal[key] = normalize_relative_path(proposal[key], key)
    return proposal, observation


def write_confirmed_artifact(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    lgwf_dir.mkdir(parents=True, exist_ok=True)
    confirmed_payload, observation = resolve_validated_payload(lgwf_dir)
    confirmed = {
        "artifact_kind": "step_designs",
        "artifact_path": f".lgwf/{OUTPUT_FILE}",
        "source_proposal_file": f".lgwf/{PROPOSAL_FILE}",
        "source_structural_gate_file": f".lgwf/{OBSERVATION_FILE}",
        "decision": "validated",
        "proposal_hash": observation.get("proposal_hash"),
        "confirmed": confirmed_payload,
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
