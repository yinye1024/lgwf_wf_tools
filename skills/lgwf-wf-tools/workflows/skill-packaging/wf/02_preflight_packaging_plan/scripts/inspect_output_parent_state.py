"""检查输出父目录状态与覆盖风险。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact, write_json


def main() -> None:
    root = Path.cwd()
    request = load_lgwf_artifact(root, "packaging_request.json")
    write_scope = load_lgwf_artifact(root, "packaging_write_scope.json")

    output_parent_abs = Path(str(request["output_parent_abs"]))
    output_skill_abs = Path(str(write_scope["output_skill_abs"]))
    target_exists = output_skill_abs.exists()
    force = bool(request.get("force", False))
    preflight = load_lgwf_artifact(root, "packaging_preflight.json")
    preflight["output"] = {
        "output_parent_abs": str(output_parent_abs),
        "output_skill_abs": str(output_skill_abs),
        "output_parent_exists": output_parent_abs.exists(),
        "target_exists": target_exists,
        "force": force,
        "overwrite_requires_confirmation": target_exists,
        "issues": [] if not target_exists or force else ["输出目录已存在，未开启 force"],
    }
    write_json(root / ".lgwf" / "packaging_preflight.json", preflight)
    print(json.dumps({"skill_packaging.preflight": preflight}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
