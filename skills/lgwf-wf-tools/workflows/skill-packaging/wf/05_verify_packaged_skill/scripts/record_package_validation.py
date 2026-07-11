"""固化打包验证结果。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object, write_json


def main() -> None:
    root = Path.cwd()
    context = read_stdin_object()
    if not context:
        raise ValueError("package_validation_context 不能为空")

    audit_check = context.get("checks", {}).get("audit_smoke", {})
    audit_ok = bool(audit_check.get("ok")) or bool(audit_check.get("skipped"))
    issues = list(context.get("issues", []))
    payload = {
        "passed": not issues and audit_ok,
        "workflow_name": "skill-packaging",
        "output_skill_abs": context.get("output_skill_abs"),
        "source_skill_abs": context.get("source_skill_abs"),
        "issues": issues,
        "checks": context.get("checks", {}),
        "summary": "打包产物验证通过。" if not issues and audit_ok else "打包产物验证失败，请查看 issues 和 audit 结果。",
    }
    write_json(root / ".lgwf" / "package_validation.json", payload)
    print(
        json.dumps(
            {"skill_packaging.package_validation": payload},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

