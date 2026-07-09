"""把 bundled runtime 复制到打包产物。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import copy_tree_filtered, read_stdin_object, remove_existing_output, summarize_tree


def main() -> None:
    context = read_stdin_object()
    if not context:
        raise ValueError("materialization_context 不能为空")

    output_skill_abs = Path(str(context["output_skill_abs"]))
    runtime_source_abs = Path(str(context["runtime_source_abs"]))
    target_runtime_abs = output_skill_abs / "vendor" / "lgwf-client-assist"
    target_runtime_abs.parent.mkdir(parents=True, exist_ok=True)
    if target_runtime_abs.exists():
        remove_existing_output(target_runtime_abs)
    copy_tree_filtered(runtime_source_abs, target_runtime_abs)

    generated_outputs = list(context.get("generated_outputs", []))
    generated_outputs.append("vendor/lgwf-client-assist")
    context["generated_outputs"] = sorted(set(generated_outputs))
    context["embedded_runtime"] = {
        **summarize_tree(target_runtime_abs),
        "relative_path": "vendor/lgwf-client-assist",
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

