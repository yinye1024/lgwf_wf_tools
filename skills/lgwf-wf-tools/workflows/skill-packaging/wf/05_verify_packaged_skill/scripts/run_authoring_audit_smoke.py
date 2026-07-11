"""对打包产物执行 authoring audit smoke。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object, run_audit


def main() -> None:
    context = read_stdin_object()
    if not context:
        raise ValueError("package_validation_context 不能为空")

    output_skill_abs = Path(str(context["output_skill_abs"]))
    audit_smoke = bool(context.get("audit_smoke", True))
    audit_result = {
        "ok": False,
        "skipped": not audit_smoke,
        "exit_code": None,
        "stdout": "",
        "stderr": "",
    }
    audit_issues: list[str] = []

    if audit_smoke:
        lgwf_py = output_skill_abs / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
        workflow_lgwf = output_skill_abs / "wf" / "workflow.lgwf"
        audit_result = run_audit(lgwf_py, workflow_lgwf, output_skill_abs)
        audit_result["skipped"] = False
        if not audit_result.get("ok", False):
            audit_issues.append("authoring audit smoke 失败")

    issues = list(context.get("issues", []))
    issues.extend(audit_issues)
    context["issues"] = issues
    context.setdefault("checks", {})["audit_smoke"] = audit_result
    print(
        json.dumps(
            {"skill_packaging.package_validation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

