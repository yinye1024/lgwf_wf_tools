"""汇总打包结果上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact


def _load_confirmed_plan(root: Path) -> dict[str, Any]:
    confirmed_artifact = load_lgwf_artifact(root, "confirmed_packaging_plan.json")
    plan = confirmed_artifact.get("confirmed")
    if not isinstance(plan, dict):
        raise ValueError("confirmed_packaging_plan.json 缺少 confirmed 对象")
    return plan


def main() -> None:
    root = Path.cwd()
    plan = _load_confirmed_plan(root)
    materialized = load_lgwf_artifact(root, "materialized_package.json")
    validation = load_lgwf_artifact(root, "package_validation.json")

    passed = bool(validation.get("passed", False))
    next_actions = (
        [
            "按打包产物目录运行一次本地 smoke，确认 workflow 入口与 ws work dir 行为符合预期。",
            "如果需要治理接入，再单独评估 facade registry.kind 与兼容 CLI 的切换策略。",
        ]
        if passed
        else [
            "根据 package_validation.json 中的 issues 修复结构或 runtime 问题。",
            "修复后重新执行 authoring audit smoke 与最小结构验证。",
        ]
    )
    summary = {
        "status": "ok" if passed else "failed",
        "workflow_name": "skill-packaging",
        "source_skill": plan.get("source_skill", {}),
        "output": plan.get("output", {}),
        "materialized_package": materialized,
        "validation": validation,
        "next_actions": next_actions,
        "report_path": "reports/skill-packaging/packaging_result_report.md",
    }
    print(
        json.dumps(
            {"skill_packaging.summary_context": summary},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

