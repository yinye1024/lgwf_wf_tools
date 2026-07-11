from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import read_json


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    summary = read_json(lgwf_dir / "maintenance_gate_summary.json")
    results = read_json(lgwf_dir / "verification_results.json")
    report_path = root / "reports" / "wf-maintenance-gate" / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# wf-maintenance-gate 报告",
        "",
        "## 结论",
        f"- 状态：`{summary.get('status', 'needs_review')}`",
        f"- 风险等级：`{summary.get('risk', 'medium')}`",
        f"- 一句话原因：{'; '.join(summary.get('next_actions', [])[:1]) or '无'}",
        "",
        "## 影响范围",
        f"- 分类：{', '.join(summary.get('impact_summary', {}).get('categories', [])) or '无'}",
        f"- 受影响 workflow：{', '.join(summary.get('impact_summary', {}).get('impacted_workflows', [])) or '无'}",
        f"- 歧义项：{json.dumps(summary.get('impact_summary', {}).get('ambiguities', []), ensure_ascii=False)}",
        "",
        "## 验证执行",
    ]
    for item in results.get("commands", []):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- {item.get('check_id')}: {item.get('status')}，耗时 {item.get('duration_ms')} ms，stdout 摘要：{item.get('stdout_summary', '') or '无'}"
        )
    for item in results.get("skipped", []):
        if isinstance(item, dict):
            lines.append(f"- 跳过 {item.get('check_id')}: {item.get('reason')}")

    lines.extend(
        [
            "",
            "## 失败与路由",
        ]
    )
    for item in summary.get("failure_routes", []):
        if isinstance(item, dict):
            lines.append(f"- {item.get('failure_type')}: 建议 `{item.get('route')}`，原因：{item.get('reason')}")
    if not summary.get("failure_routes"):
        lines.append("- 无")

    lines.extend(
        [
            "",
            "## 产物路径",
        ]
    )
    for path in summary.get("artifact_paths", []):
        lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## 后续动作",
        ]
    )
    for action in summary.get("next_actions", []):
        lines.append(f"- {action}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": "ok", "report_path": "reports/wf-maintenance-gate/report.md"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
