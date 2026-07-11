from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
SHARED_SCRIPT_CANDIDATES = [
    SCRIPT_PATH.parents[2] / "shared" / "scripts",
    SCRIPT_PATH.parents[3] / "wf" / "shared" / "scripts",
]
for candidate in SHARED_SCRIPT_CANDIDATES:
    if (candidate / "repo_context_runtime.py").is_file():
        sys.path.insert(0, str(candidate))
        break
else:
    raise RuntimeError(f"无法定位 repo_context_runtime.py: {SCRIPT_PATH}")

from repo_context_runtime import run_stage


if __name__ == "__main__":
    run_stage("workflow_summary_handoff", Path(__file__).resolve())
