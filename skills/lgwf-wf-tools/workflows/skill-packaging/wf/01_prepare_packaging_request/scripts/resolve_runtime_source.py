"""解析并校验 runtime 来源。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import default_runtime_source, load_lgwf_artifact, read_stdin_object, resolve_user_path, validate_runtime, write_json


def main() -> None:
    root = Path.cwd()
    request = read_stdin_object()
    if not request:
        request = load_lgwf_artifact(root, "packaging_request.json")
    raw_runtime = str(request.get("runtime_source", "")).strip()
    runtime_abs = resolve_user_path(root, raw_runtime) if raw_runtime else default_runtime_source(root)
    issues = validate_runtime(runtime_abs)
    request["runtime_source"] = raw_runtime or str(runtime_abs)
    request["runtime_source_abs"] = str(runtime_abs)
    resolution = {
        "runtime_source_abs": str(runtime_abs),
        "defaulted": not raw_runtime,
        "ok": not issues,
        "issues": issues,
    }
    lgwf_dir = root / ".lgwf"
    write_json(lgwf_dir / "packaging_request.json", request)
    write_json(lgwf_dir / "runtime_source_resolution.json", resolution)
    print(
        json.dumps(
            {
                "skill_packaging.packaging_request": request,
                "skill_packaging.runtime_resolution": resolution,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
