from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, load_runtime_context, output_state, run_audit, write_json


def main() -> None:
    context = load_runtime_context()
    target = Path(str(context["normalized_target_workflow_lgwf"]))
    result = run_audit(target)
    write_json(lgwf_dir() / "initial_audit_result.json", result)
    output_state({"initial_audit_result": result})


if __name__ == "__main__":
    main()
