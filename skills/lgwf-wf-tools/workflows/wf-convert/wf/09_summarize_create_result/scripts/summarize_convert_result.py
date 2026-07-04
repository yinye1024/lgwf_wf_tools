from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def as_lines(values: Any) -> list[str]:
    if isinstance(values, list):
        return [str(item) for item in values]
    if values:
        return [str(values)]
    return ["无"]


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# wf-convert 转换结果汇总",
        "",
        f"- workflow: `{summary.get('workflow_name', 'wf-convert')}`",
        "",
        "## 源工作流分析",
        "",
    ]
    lines.extend(f"- {item}" for item in as_lines(summary.get("analysis_summary")))
    lines.extend(["", "## 已确认输入", ""])
    lines.extend(f"- {item}" for item in as_lines(summary.get("approved_input_summary")))
    lines.extend(["", "## Payload", ""])
    lines.extend(f"- {item}" for item in as_lines(summary.get("payload_summary")))
    lines.extend(["", "## 业务一致性审查", ""])
    parity = summary.get("business_parity")
    if isinstance(parity, dict):
        lines.append(f"- verdict: `{parity.get('parity_verdict', 'unknown')}`")
        lines.append(f"- report: `{parity.get('report_path', '.lgwf/business_parity_report.json')}`")
        missing = as_lines(parity.get("missing_business_rules"))
        lines.extend(f"- missing_business_rule: {item}" for item in missing)
    else:
        lines.append("- 未生成业务一致性审查报告")
    lines.extend(["", "## 未解决风险", ""])
    lines.extend(f"- {item}" for item in as_lines(summary.get("risks")))
    lines.append("")
    return "\n".join(lines)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    inspection = load_json(lgwf_dir / "prompt_workflow_inspection.json")
    payload = load_json(lgwf_dir / "wf_create_payload.json")
    parity = load_json(lgwf_dir / "business_parity_report.json")
    report = render_report(
        {
            "workflow_name": payload.get("prompt_convert_payload", {}).get("workflow_name", "wf-convert"),
            "analysis_summary": inspection.get("source_summary", []),
            "approved_input_summary": ["创建输入包已通过人工确认"],
            "payload_summary": [".lgwf/wf_create_payload.json"],
            "business_parity": parity,
            "risks": inspection.get("risks", []),
        }
    )
    report_path = root / "reports" / "convert-workflow" / "convert_result_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    result = {"report_path": "reports/convert-workflow/convert_result_report.md"}
    print(json.dumps({"lgwf_wf_convert.summary_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
