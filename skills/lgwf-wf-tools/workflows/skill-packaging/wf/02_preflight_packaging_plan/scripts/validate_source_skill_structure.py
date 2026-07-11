"""校验源 skill 基本结构。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact, validate_source_skill, write_json


def main() -> None:
    root = Path.cwd()
    request = load_lgwf_artifact(root, "packaging_request.json")
    source_skill_abs = Path(str(request["source_skill_abs"]))
    issues = validate_source_skill(source_skill_abs)
    preflight = load_lgwf_artifact(root, "packaging_preflight.json")
    preflight["source_skill"] = {
        "path": str(source_skill_abs),
        "ok": not issues,
        "issues": issues,
    }
    write_json(root / ".lgwf" / "packaging_preflight.json", preflight)
    print(json.dumps({"skill_packaging.preflight": preflight}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
