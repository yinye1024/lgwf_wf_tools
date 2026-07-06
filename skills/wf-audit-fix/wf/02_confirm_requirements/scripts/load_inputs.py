from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import load_input, lgwf_dir, output_state, write_json


def main() -> None:
    data = load_input()
    write_json(lgwf_dir() / "input.json", data)
    output_state({"input_payload": data})


if __name__ == "__main__":
    main()
