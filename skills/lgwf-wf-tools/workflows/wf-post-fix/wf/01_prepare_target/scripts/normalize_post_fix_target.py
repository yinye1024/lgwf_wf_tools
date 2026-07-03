from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import lgwf_dir, output_state, read_json, write_json


def normalize_target(raw: dict[str, Any]) -> dict[str, Any]:
    target = raw.get("post_fix_target") if isinstance(raw.get("post_fix_target"), dict) else raw
    if not isinstance(target, dict):
        raise ValueError("post_fix_target must be a JSON object")
    workflow = target.get("target_workflow_lgwf")
    if not isinstance(workflow, str) or not workflow.strip():
        raise ValueError("target_workflow_lgwf is required")
    workflow_path = Path(workflow).expanduser()
    package_root = target.get("target_package_root")
    if not isinstance(package_root, str) or not package_root.strip():
        package_root = str(workflow_path.parent)
    target_dirs = target.get("target_dirs")
    if not isinstance(target_dirs, list) or not target_dirs:
        target_dirs = [package_root]
    mode = target.get("mode", "manual")
    if mode not in {"manual", "auto"}:
        raise ValueError("mode must be manual or auto")
    return {
        "target_workflow_lgwf": str(workflow_path),
        "target_package_root": str(Path(package_root).expanduser()),
        "target_dirs": [str(Path(str(item)).expanduser()) for item in target_dirs],
        "mode": mode,
    }


def main() -> None:
    request = read_json(lgwf_dir() / "post_fix_target.request.json", {})
    target = normalize_target(request if isinstance(request, dict) else {})
    write_json(lgwf_dir() / "post_fix_target.json", target)
    write_json(lgwf_dir() / "post_fix_decisions.json", {"auto_enabled": target["mode"] == "auto", "stages": []})
    write_json(lgwf_dir() / "post_fix_stage_results.json", {"stages": []})
    output_state({"post_fix_target": target, "post_fix_decisions": {"auto_enabled": target["mode"] == "auto", "stages": []}})


if __name__ == "__main__":
    main()
