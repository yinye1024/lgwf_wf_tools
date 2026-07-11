"""冻结允许写入范围。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact, output_skill_path, read_stdin_object, write_json


def main() -> None:
    root = Path.cwd()
    request = read_stdin_object()
    if not request:
        request = load_lgwf_artifact(root, "packaging_request.json")
    path_context = load_lgwf_artifact(root, "packaging_path_context.json")
    runtime_resolution = load_lgwf_artifact(root, "runtime_source_resolution.json")

    source_skill_abs = Path(str(request["source_skill_abs"]))
    output_parent_abs = Path(str(request["output_parent_abs"]))
    output_skill_abs = output_skill_path(source_skill_abs, output_parent_abs)
    write_scope = {
        "allowed_write_root_abs": str(output_parent_abs),
        "output_skill_abs": str(output_skill_abs),
        "force": bool(request.get("force", False)),
        "audit_smoke": bool(request.get("audit_smoke", True)),
        "notes": [
            "真实写入只允许落到 output_parent/<source-skill-name>/。",
            "运行状态只允许留在 work_dir/.lgwf。",
        ],
    }
    path_context.update(
        {
            "output_skill_abs": str(output_skill_abs),
            "allowed_write_root_abs": str(output_parent_abs),
            "runtime_source_abs": runtime_resolution.get("runtime_source_abs", ""),
            "runtime_defaulted": runtime_resolution.get("defaulted", False),
        }
    )

    lgwf_dir = root / ".lgwf"
    write_json(lgwf_dir / "packaging_write_scope.json", write_scope)
    print(
        json.dumps(
            {
                "skill_packaging.path_context": path_context,
                "skill_packaging.write_scope": write_scope,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
