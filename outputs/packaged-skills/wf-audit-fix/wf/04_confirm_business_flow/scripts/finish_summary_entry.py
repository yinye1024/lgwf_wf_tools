from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import output_state


def main() -> None:
    output_state({"real_audit_gate_terminal": "summary"})


if __name__ == "__main__":
    main()
