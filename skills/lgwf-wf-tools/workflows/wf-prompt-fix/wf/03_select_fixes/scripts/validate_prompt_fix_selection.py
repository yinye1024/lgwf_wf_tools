from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def _issue_ids(audit: dict[str, Any]) -> list[str]:
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    ids = []
    for index, issue in enumerate(issues, start=1):
        if isinstance(issue, dict):
            ids.append(str(issue.get("id") or f"prompt_issue_{index}"))
    return ids


def normalize_selection(raw: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    ids = _issue_ids(audit)
    selected_raw = raw.get("selected_issue_ids", [])
    if not isinstance(selected_raw, list):
        selected_raw = []
    if raw.get("skip_fix"):
        selected: list[str] = []
        skip_fix = True
    elif raw.get("fix_all"):
        selected = ids
        skip_fix = False
    else:
        selected = [str(item) for item in selected_raw if str(item) in ids]
        skip_fix = not selected
    return {
        "artifact_root": ".lgwf/prompt_acceptance",
        "fix_all": bool(raw.get("fix_all")) and not skip_fix,
        "selected_issue_ids": selected,
        "skip_fix": skip_fix,
        "comment": str(raw.get("comment") or ""),
    }


def choose_route(selection: dict[str, Any], audit: dict[str, Any]) -> str:
    if selection.get("skip_fix"):
        return "summarize"
    if selection.get("selected_issue_ids"):
        return "fix"
    return "summarize"


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    audit = read_json(root / "audit.json", {})
    raw = read_json(root / "fix_selection.json", {})
    if not isinstance(audit, dict):
        audit = {}
    if not isinstance(raw, dict):
        raw = {}
    selection = normalize_selection(raw, audit)
    write_json(root / "fix_selection.json", selection)
    output_state({"prompt_fix_selection": selection})


if __name__ == "__main__":
    main()
