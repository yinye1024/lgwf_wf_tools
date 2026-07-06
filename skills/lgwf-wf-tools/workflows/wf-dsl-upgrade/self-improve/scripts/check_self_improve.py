from __future__ import annotations

import json
from pathlib import Path


WORKFLOW_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    required = [
        WORKFLOW_ROOT / "AGENTS.md",
        WORKFLOW_ROOT / "wf" / "workflow.lgwf",
        WORKFLOW_ROOT / "entry_contract.json",
        WORKFLOW_ROOT / "self-improve" / "manifest.json",
    ]
    missing = [str(path.relative_to(WORKFLOW_ROOT)) for path in required if not path.exists()]
    payload = {"passed": not missing, "missing": missing}
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
