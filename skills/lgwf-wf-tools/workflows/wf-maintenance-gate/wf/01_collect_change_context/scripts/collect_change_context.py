from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import find_workspace_root, normalize_repo_path, read_json, write_json


def parse_git_status(workspace_root: Path) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=workspace_root,
        text=True,
        capture_output=True,
        check=False,
    )
    entries: list[dict[str, str]] = []
    for raw_line in completed.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        status = raw_line[:2]
        payload = raw_line[3:].strip()
        old_path = ""
        new_path = payload
        if " -> " in payload:
            old_path, new_path = payload.split(" -> ", 1)
        change_kind = {
            "??": "untracked",
            " M": "modified",
            "M ": "modified",
            "A ": "added",
            "D ": "deleted",
            "R ": "renamed",
        }.get(status, "modified")
        entries.append(
            {
                "path": normalize_repo_path(new_path),
                "old_path": normalize_repo_path(old_path) if old_path else "",
                "change_kind": change_kind,
                "git_status_code": status,
            }
        )
    return entries


def load_registry_workflows(workspace_root: Path) -> list[dict[str, str]]:
    registry_path = workspace_root / "skills" / "lgwf-wf-tools" / "registry.json"
    registry = read_json(registry_path)
    workflows = registry.get("workflows", [])
    if not isinstance(workflows, list):
        return []
    result: list[dict[str, str]] = []
    for item in workflows:
        if isinstance(item, dict):
            result.append(
                {
                    "id": str(item.get("id", "")).strip(),
                    "kind": str(item.get("kind", "")).strip(),
                }
            )
    return [item for item in result if item["id"]]


def main() -> None:
    root = Path.cwd()
    workspace_root = find_workspace_root(root)
    lgwf_dir = root / ".lgwf"
    request = read_json(lgwf_dir / "maintenance_gate_request.json")
    path_context = read_json(lgwf_dir / "path_context.json")
    explicit_files = request.get("changed_files", [])
    files: list[dict[str, str]]
    if isinstance(explicit_files, list) and explicit_files:
        files = [
            {
                "path": normalize_repo_path(str(path)),
                "old_path": "",
                "change_kind": "provided",
                "git_status_code": "",
            }
            for path in explicit_files
        ]
        change_source = "explicit_input"
    else:
        files = parse_git_status(workspace_root)
        change_source = "git_status"

    change_context = {
        "artifact_kind": "change_context",
        "request": request,
        "change_source": change_source,
        "files": files,
        "registry_workflows": load_registry_workflows(workspace_root),
        "path_context": path_context,
    }
    write_json(lgwf_dir / "change_context.json", change_context)
    print(
        json.dumps(
            {"wf_maintenance_gate.change_context": change_context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
