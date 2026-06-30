from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main() -> None:
    cwd = Path.cwd()
    lgwf_dir = cwd / ".lgwf"
    reports_dir = cwd / "reports" / "lgwf-wf-thinking"
    reports_dir.mkdir(parents=True, exist_ok=True)

    confirmed = read_json(lgwf_dir / "confirmed_composition_plan.json")
    plan = confirmed.get("plan", {})
    sequence = plan.get("workflow_sequence", []) if isinstance(plan, dict) else []
    handoff = {
        "operator": "lgwf-wf-tools",
        "workflow_sequence": sequence,
        "handoff_inputs": plan.get("handoff_inputs", {}) if isinstance(plan, dict) else {},
        "approval_points": plan.get("approval_points", []) if isinstance(plan, dict) else [],
        "acceptance": plan.get("acceptance", []) if isinstance(plan, dict) else [],
        "source_skill": "lgwf-wf-thinking",
    }
    (lgwf_dir / "handoff_instructions.json").write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# lgwf-wf-thinking handoff",
        "",
        "## 下一执行方",
        "",
        "`lgwf-wf-tools`",
        "",
        "## Workflow 顺序",
        "",
    ]
    if sequence:
        for item in sequence:
            lines.append(f"- `{item.get('workflow_id', '')}`：{item.get('purpose', '')}")
    else:
        lines.append("- 未生成可执行 workflow 顺序，请回到 `confirm_plan` 补齐。")
    lines.extend(
        [
            "",
            "## 执行边界",
            "",
            "- 本 skill 不直接执行下游 workflow。",
            "- 实际运行、审批代理、监控和 resume/rerun 由 `lgwf-wf-tools` 接管。",
        ]
    )
    (reports_dir / "handoff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"lgwf_wf_thinking.handoff": handoff}, ensure_ascii=False))


if __name__ == "__main__":
    main()
