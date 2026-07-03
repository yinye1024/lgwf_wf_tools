from __future__ import annotations

import json
import sys


def main() -> None:
    raw = sys.stdin.read().strip()
    child_result = json.loads(raw) if raw else {}
    summary = {
        "status": child_result.get("status") if isinstance(child_result, dict) else None,
        "result": child_result,
    }
    print(json.dumps({"lgwf_wf_convert.wf_create_result_summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
