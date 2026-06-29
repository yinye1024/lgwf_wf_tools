from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import lgwf_dir, load_self_fix_target, output_state, read_json


def build_context(contract: dict, target: dict) -> dict:
    return {
        "target_workflow_lgwf": target.get("target_workflow_lgwf"),
        "target_package_root": target.get("target_package_root"),
        "contract": contract,
        "instruction": "Return the target workflow startup parameters as a JSON object. This value is persisted to .lgwf/target_workflow_input.json and reused for every retry.",
    }


def main() -> None:
    contract = read_json(lgwf_dir() / "target_input_contract.json", {})
    if not isinstance(contract, dict):
        raise ValueError(".lgwf/target_input_contract.json must contain a JSON object")
    target = load_self_fix_target()
    output_state({"input_collection_context": build_context(contract, target)})


if __name__ == "__main__":
    main()
