from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import ensure_workflow_file, lgwf_dir, normalize_path, output_state, read_json, save_runtime_context


def main() -> None:
    data = read_json(lgwf_dir() / "input.json", {})
    target = normalize_path(str(data.get("target_workflow_lgwf", "")))
    ensure_workflow_file(target)
    context = {
        "normalized_target_workflow_lgwf": str(target),
        "resolved_target_package_root": str(target.parent.parent if target.parent.name == "wf" else target.parent),
    }
    save_runtime_context(context)
    output_state(context)


if __name__ == "__main__":
    main()
