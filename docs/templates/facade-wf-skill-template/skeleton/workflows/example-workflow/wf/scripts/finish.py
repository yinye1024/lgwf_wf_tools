from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    work_dir = Path(os.environ.get("LGWF_WORK_DIR", ".")).resolve()
    output = work_dir / ".lgwf" / "example_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "ok",
        "message": "example workflow finished",
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
