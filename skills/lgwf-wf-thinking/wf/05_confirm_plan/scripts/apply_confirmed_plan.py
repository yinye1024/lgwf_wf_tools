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


def normalize_tuning(raw: object) -> dict[str, list[Any]]:
    if not isinstance(raw, dict):
        raw = {}
    normalized: dict[str, list[Any]] = {}
    for key in ("workflow_sequence_changes", "extra_constraints", "acceptance_changes"):
        value = raw.get(key, []) if isinstance(raw, dict) else []
        normalized[key] = value if isinstance(value, list) else [value]
    return normalized


def has_tuning_items(tuning: dict[str, list[Any]]) -> bool:
    return any(bool(items) for items in tuning.values())


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    plan = read_json(lgwf_dir / "composition_plan.json")
    decision = read_json(lgwf_dir / "composition_plan_decision.json")
    decision_value = decision.get("decision")
    tuning = normalize_tuning(decision.get("tuning"))
    if decision_value != "approve":
        raise SystemExit(
            f"只允许在 decision=approve 时生成 confirmed_composition_plan.json，当前为 {decision_value!r}。"
        )
    if has_tuning_items(tuning):
        raise SystemExit("decision=approve 时 tuning 必须全部为空数组；请改为 revise 或先清空未消费修订。")
    approved = {
        "plan": plan,
        "decision": decision,
        "status": "approved",
        "next_operator": "lgwf-wf-tools",
        "execution_boundary": "lgwf-wf-thinking 只生成执行引导，实际运行由 lgwf-wf-tools 负责。",
    }
    approved["tuning"] = tuning
    (lgwf_dir / "confirmed_composition_plan.json").write_text(
        json.dumps(approved, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_wf_thinking.confirmed_composition_plan": approved}, ensure_ascii=False))


if __name__ == "__main__":
    main()
