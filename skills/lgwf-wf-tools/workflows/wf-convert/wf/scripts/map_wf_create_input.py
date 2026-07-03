from __future__ import annotations

import json
import sys


def main() -> None:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    child_input = payload.get("wf_create_payload") if isinstance(payload, dict) else None
    if not isinstance(child_input, dict):
        raise ValueError("wf_create_payload 缺少 wf-create 输入")
    print(json.dumps({"lgwf_wf_convert.wf_create_input": child_input}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
