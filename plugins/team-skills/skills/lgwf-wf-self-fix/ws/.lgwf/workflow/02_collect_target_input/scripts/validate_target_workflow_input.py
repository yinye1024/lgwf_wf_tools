from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json, write_json


def load_target_input(path: Path) -> dict:
    data = read_json(path, None)
    if not isinstance(data, dict):
        raise ValueError(".lgwf/target_workflow_input.json must contain a JSON object")
    return data


def main() -> None:
    path = lgwf_dir() / "target_workflow_input.json"
    target_input = load_target_input(path)
    write_json(path, target_input)
    append_history({"event": "target_input_validated", "keys": sorted(target_input.keys())})
    output_state({"target_workflow_input_valid": True, "target_workflow_input_keys": sorted(target_input.keys())})


if __name__ == "__main__":
    main()
