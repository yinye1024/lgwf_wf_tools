"""生成打包产物清单文件。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object, write_packaging_manifest


def main() -> None:
    context = read_stdin_object()
    if not context:
        raise ValueError("materialization_context 不能为空")

    source_skill_abs = Path(str(context["source_skill_abs"]))
    output_skill_abs = Path(str(context["output_skill_abs"]))
    runtime_source_abs = Path(str(context["runtime_source_abs"]))
    manifest_path = write_packaging_manifest(source_skill_abs, output_skill_abs, runtime_source_abs)

    generated_outputs = list(context.get("generated_outputs", []))
    generated_outputs.append("PACKAGING_MANIFEST.json")
    context["generated_outputs"] = sorted(set(generated_outputs))
    context["packaging_manifest"] = {
        "path": str(manifest_path),
        "relative_path": "PACKAGING_MANIFEST.json",
    }
    print(
        json.dumps(
            {"skill_packaging.materialization_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

