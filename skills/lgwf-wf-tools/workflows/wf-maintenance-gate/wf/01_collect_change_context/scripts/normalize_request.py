from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import (
    bool_value,
    find_workspace_root,
    normalize_repo_path,
    path_is_safe,
    read_stdin_object,
    unique_in_order,
    write_json,
)


def main() -> None:
    root = Path.cwd()
    workspace_root = find_workspace_root(root)
    payload = read_stdin_object()
    request = payload.get("maintenance_gate_request", payload)
    if not isinstance(request, dict):
        request = {}

    changed_files: list[str] = []
    rejected_paths: list[str] = []
    for raw in request.get("changed_files", []) or []:
        text = normalize_repo_path(str(raw))
        if path_is_safe(text):
            changed_files.append(text)
        else:
            rejected_paths.append(str(raw))

    target_workflows = unique_in_order(
        [str(item).strip() for item in request.get("target_workflows", []) or [] if str(item).strip()]
    )
    normalized_request = {
        "scope": str(request.get("scope", "auto")).strip() or "auto",
        "changed_files": unique_in_order(changed_files),
        "target_workflows": target_workflows,
        "intent": str(request.get("intent", "maintenance")).strip() or "maintenance",
        "verification_level": str(request.get("verification_level", "standard")).strip() or "standard",
        "allow_deep_doctor": bool_value(request.get("allow_deep_doctor"), False),
        "allow_workflow_tests": bool_value(request.get("allow_workflow_tests"), True),
        "allow_pre_release": bool_value(request.get("allow_pre_release"), False),
        "allow_package_smoke": bool_value(request.get("allow_package_smoke"), False),
        "output_zip": request.get("output_zip"),
        "rejected_paths": rejected_paths,
    }
    path_context = {
        "workspace_root": str(workspace_root),
        "work_dir": str(root.resolve()),
        "facade_root": "skills/lgwf-wf-tools",
        "registry_path": "skills/lgwf-wf-tools/registry.json",
        "workflows_root": "skills/lgwf-wf-tools/workflows",
    }

    lgwf_dir = root / ".lgwf"
    write_json(lgwf_dir / "maintenance_gate_request.json", normalized_request)
    write_json(lgwf_dir / "path_context.json", path_context)
    print(
        json.dumps(
            {
                "wf_maintenance_gate.maintenance_gate_request": normalized_request,
                "wf_maintenance_gate.path_context": path_context,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
