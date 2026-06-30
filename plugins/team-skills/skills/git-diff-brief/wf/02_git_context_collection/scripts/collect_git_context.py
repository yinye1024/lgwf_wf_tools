from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_changed_files_index(diff_names: list[str], status_lines: list[str]) -> dict[str, Any]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in [*diff_names, *status_lines]:
        value = str(raw).strip()
        if not value:
            continue
        if " " in value and not value.startswith(("docs/", "wf/", "src/", "tests/")):
            parts = value.split(maxsplit=1)
            path = parts[1].strip() if len(parts) == 2 else parts[0].strip()
        else:
            path = value
        if path and path not in seen:
            seen.add(path)
            ordered.append(path)
    return {"files": ordered, "count": len(ordered)}


def build_snapshot(repo_path: str = ".", diff_text: str = "", diff_names: list[str] | None = None) -> dict[str, Any]:
    diff_names = diff_names or []
    status_lines = [f"M {name}" for name in diff_names]
    changed_files_index = build_changed_files_index(diff_names=diff_names, status_lines=status_lines)
    return {
        "git_diff_snapshot": {
            "diff_text": diff_text,
            "diff_name_only": diff_names,
            "status_lines": status_lines,
        },
        "latest_commit_context": {
            "commit_hash": "",
            "subject": "",
            "body": "",
        },
        "changed_files_index": changed_files_index,
        "git_collection_log": {
            "repo_path": repo_path,
            "status": "placeholder",
            "warnings": [
                "当前为 workflow 初稿脚本，占位输出需在接入真实 Git 命令后补齐。",
            ],
        },
    }


def main() -> None:
    snapshot = build_snapshot()
    output_path = Path(".lgwf/git_context_snapshot.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.git_context_snapshot": snapshot,
        "git_diff_brief.git_diff_snapshot": snapshot["git_diff_snapshot"],
        "git_diff_brief.latest_commit_context": snapshot["latest_commit_context"],
        "git_diff_brief.changed_files_index": snapshot["changed_files_index"],
        "git_diff_brief.git_collection_log": snapshot["git_collection_log"],
        "git_diff_brief.git_context_collection_result": {
            "ok": True,
            "placeholder": True,
            "output_file": ".lgwf/git_context_snapshot.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
