from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path.cwd()
    approval_path = root / ".lgwf" / "wf_create_input_approval.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    value = approval.get("value", approval)
    decision = str(value.get("decision", value.get("approval", ""))).lower() if isinstance(value, dict) else ""
    if decision != "approve":
        raise ValueError("只有 approve 决策可以 finalize create input")
    result = {"decision": "approve", "approval_path": ".lgwf/wf_create_input_approval.json"}
    print(json.dumps({"lgwf_wf_convert.finalize_create_input_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

