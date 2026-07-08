from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
LGWF_PY = SKILL_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = [
        sys.executable,
        str(LGWF_PY),
        "run",
        "--workflow-lgwf",
        "wf/workflow.lgwf",
        "--work-dir",
        "ws",
        *args,
    ]
    completed = subprocess.run(command, cwd=str(SKILL_ROOT))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
