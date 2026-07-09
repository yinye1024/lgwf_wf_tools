"""生成打包产物本地运行入口。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object, write_local_runner


def main() -> None:
    context = read_stdin_object()
    if not context:
        raise ValueError("materialization_context 不能为空")

    output_skill_abs = Path(str(context["output_skill_abs"]))
    runner_path = write_local_runner(output_skill_abs)
    generated_outputs = list(context.get("generated_outputs", []))
    generated_outputs.append("scripts/run_local_lgwf_workflow.py")
    context["generated_outputs"] = sorted(set(generated_outputs))
    context["local_runner"] = {
        "path": str(runner_path),
        "relative_path": "scripts/run_local_lgwf_workflow.py",
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

