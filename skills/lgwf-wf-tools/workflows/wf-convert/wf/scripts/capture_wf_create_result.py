from __future__ import annotations

import json
import sys
from typing import Any


def find_create_summary(child_result: dict[str, Any]) -> dict[str, Any]:
    final_state = child_result.get("final_state")
    if not isinstance(final_state, dict):
        return {}
    namespaced = final_state.get("lgwf_wf_create")
    if isinstance(namespaced, dict) and isinstance(namespaced.get("summary_result"), dict):
        return namespaced["summary_result"]
    direct = final_state.get("lgwf_wf_create.summary_result")
    if isinstance(direct, dict):
        return direct
    return {}


def build_summary(child_result: dict[str, Any]) -> dict[str, Any]:
    create_summary = find_create_summary(child_result)
    summary = {
        "status": child_result.get("status") if isinstance(child_result, dict) else None,
        "result": child_result,
    }
    if create_summary:
        summary["created_workflow"] = {
            "workflow_name": create_summary.get("workflow_name"),
            "target_package_root": create_summary.get("target_package_root"),
            "report_path": create_summary.get("report_path"),
        }
    return summary


def main() -> None:
    raw = sys.stdin.read().strip()
    child_result = json.loads(raw) if raw else {}
    if not isinstance(child_result, dict):
        raise TypeError("wf_create_result 必须是 JSON object")
    summary = build_summary(child_result)
    print(json.dumps({"lgwf_wf_convert.wf_create_result_summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
