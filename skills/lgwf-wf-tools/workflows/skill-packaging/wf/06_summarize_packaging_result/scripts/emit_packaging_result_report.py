"""生成最终打包结果报告与摘要。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import read_stdin_object, write_json


def _render_report(summary: dict[str, object]) -> str:
    validation = summary.get("validation", {}) if isinstance(summary.get("validation"), dict) else {}
    output = summary.get("output", {}) if isinstance(summary.get("output"), dict) else {}
    materialized = summary.get("materialized_package", {}) if isinstance(summary.get("materialized_package"), dict) else {}
    issues = validation.get("issues", []) if isinstance(validation, dict) else []
    next_actions = summary.get("next_actions", []) if isinstance(summary.get("next_actions"), list) else []

    lines = [
        "# skill-packaging 打包结果报告",
        "",
        f"- 最终状态：`{summary.get('status', 'unknown')}`",
        f"- 输出目录：`{output.get('output_skill_abs', materialized.get('output_skill_abs', ''))}`",
        f"- 验证通过：`{validation.get('passed', False)}`",
        "",
        "## 关键产物",
        "",
    ]
    for rel in materialized.get("generated_outputs", []):
        lines.append(f"- `{rel}`")

    lines.extend(["", "## 验证问题", ""])
    if issues:
        for issue in issues:
            lines.append(f"- {issue}")
    else:
        lines.append("- 无")

    lines.extend(["", "## 后续建议", ""])
    for action in next_actions:
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path.cwd()
    summary = read_stdin_object()
    if not summary:
        raise ValueError("summary_context 不能为空")

    report_path = root / "reports" / "skill-packaging" / "packaging_result_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(summary), encoding="utf-8")

    result = {
        **summary,
        "report_path": "reports/skill-packaging/packaging_result_report.md",
    }
    write_json(root / ".lgwf" / "packaging_result_summary.json", result)
    print(
        json.dumps(
            {"skill_packaging.summary_result": result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

