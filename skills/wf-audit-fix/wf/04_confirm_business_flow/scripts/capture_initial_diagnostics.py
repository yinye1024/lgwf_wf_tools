from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json, summarize_audit_result, write_json


def main() -> None:
    result = read_json(lgwf_dir() / "initial_audit_result.json", {})
    diagnostics = summarize_audit_result(result, label="initial_real")
    write_json(lgwf_dir() / "initial_audit_diagnostics.json", diagnostics)
    output_state({"initial_audit_diagnostics": diagnostics})


if __name__ == "__main__":
    main()
