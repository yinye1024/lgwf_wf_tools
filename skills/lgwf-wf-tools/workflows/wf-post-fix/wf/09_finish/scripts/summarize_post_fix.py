from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import (
    generated_test_files,
    generated_tests_path,
    load_decisions,
    load_stage_results,
    load_target,
    output_state,
    read_json,
    write_json,
)


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# wf-post-fix 综合后处理报告",
        "",
        f"- 目标 workflow：`{summary['target'].get('target_workflow_lgwf', '')}`",
        f"- 模式：`{summary['target'].get('mode', 'manual')}`",
        f"- 阶段数：{len(summary.get('stages', []))}",
        "",
        "## 阶段结果",
        "",
    ]
    for stage in summary.get("stages", []):
        lines.append(f"- `{stage.get('stage_id')}`：{stage.get('status')}")
    lines.extend(["", "## 生成测试入口", ""])
    for stage_id, path in summary.get("generated_tests", {}).items():
        lines.append(f"- `{stage_id}`：`{path}`")
    lines.append("")
    return "\n".join(lines)


def latest_stage_results(stages: list[Any]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        stage_id = stage.get("stage_id")
        if not isinstance(stage_id, str) or not stage_id:
            continue
        if stage_id not in latest:
            order.append(stage_id)
        latest[stage_id] = stage
    return [latest[stage_id] for stage_id in order]


def build_summary() -> dict[str, Any]:
    target = load_target()
    decisions = load_decisions()
    stage_results = load_stage_results()
    stage_history = stage_results.get("stages", [])
    if not isinstance(stage_history, list):
        stage_history = []
    generated_tests = generated_test_files(target)
    summary = {
        "target": target,
        "decisions": decisions,
        "stages": latest_stage_results(stage_history),
        "stage_history": stage_history,
        "generated_tests": generated_tests,
    }
    return summary


def main() -> None:
    summary = build_summary()
    write_json(generated_tests_path(), summary["generated_tests"])
    write_json(Path(".lgwf/post_fix_summary.json"), summary)
    report_dir = Path("reports/wf-post-fix")
    write_json(report_dir / "report.json", summary)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.md").write_text(render_report(summary), encoding="utf-8")
    output_state({"post_fix_summary": summary})


if __name__ == "__main__":
    main()
