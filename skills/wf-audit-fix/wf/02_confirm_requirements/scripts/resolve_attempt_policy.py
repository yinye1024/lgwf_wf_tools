from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json, save_runtime_context


def main() -> None:
    data = read_json(lgwf_dir() / "input.json", {})
    value = data.get("max_attempts", 5)
    try:
        attempts = int(value)
    except (TypeError, ValueError):
        attempts = 5
    attempts = max(1, min(attempts, 20))
    policy = {"max_attempts": attempts, "hard_cap": 20}
    context = read_json(lgwf_dir() / "runtime_context.json", {})
    context["attempt_policy"] = policy
    save_runtime_context(context)
    output_state({"attempt_policy": policy})


if __name__ == "__main__":
    main()
