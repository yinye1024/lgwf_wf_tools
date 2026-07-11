"""校验 runtime 来源结构。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact, validate_runtime, write_json


def main() -> None:
    root = Path.cwd()
    request = load_lgwf_artifact(root, "packaging_request.json")
    runtime_source_abs = Path(str(request["runtime_source_abs"]))
    issues = validate_runtime(runtime_source_abs)
    preflight = load_lgwf_artifact(root, "packaging_preflight.json")
    preflight["runtime"] = {
        "path": str(runtime_source_abs),
        "ok": not issues,
        "issues": issues,
    }
    write_json(root / ".lgwf" / "packaging_preflight.json", preflight)
    print(json.dumps({"skill_packaging.preflight": preflight}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
