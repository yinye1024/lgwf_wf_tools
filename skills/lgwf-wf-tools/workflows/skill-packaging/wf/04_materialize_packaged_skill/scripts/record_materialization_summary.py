"""记录打包执行摘要。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object, summarize_tree, write_json


def main() -> None:
    root = Path.cwd()
    context = read_stdin_object()
    if not context:
        raise ValueError("materialization_context 不能为空")

    output_skill_abs = Path(str(context["output_skill_abs"]))
    materialized = {
        "status": "ok",
        "workflow_name": "skill-packaging",
        "source_skill_abs": context["source_skill_abs"],
        "output_parent_abs": context["output_parent_abs"],
        "output_skill_abs": context["output_skill_abs"],
        "runtime_source_abs": context["runtime_source_abs"],
        "audit_smoke": bool(context.get("audit_smoke", True)),
        "target_existed_before_copy": bool(context.get("target_existed_before_copy", False)),
        "generated_outputs": list(context.get("generated_outputs", [])),
        "source_step_docs": list(context.get("source_step_docs", [])),
        "embedded_runtime": context.get("embedded_runtime", {}),
        "local_runner": context.get("local_runner", {}),
        "packaging_manifest": context.get("packaging_manifest", {}),
        "output_tree": summarize_tree(output_skill_abs),
        "summary": "已完成真实复制、runtime 内置、runner 生成和 manifest 生成。",
    }
    write_json(root / ".lgwf" / "materialized_package.json", materialized)
    print(
        json.dumps(
            {"skill_packaging.materialized_package": materialized},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

