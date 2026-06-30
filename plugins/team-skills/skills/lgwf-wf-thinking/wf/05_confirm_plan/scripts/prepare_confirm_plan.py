from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def normalize_tuning(raw: object) -> dict[str, list]:
    if not isinstance(raw, dict):
        raw = {}
    normalized: dict[str, list] = {}
    for key in ("workflow_sequence_changes", "extra_constraints", "acceptance_changes"):
        value = raw.get(key, []) if isinstance(raw, dict) else []
        normalized[key] = value if isinstance(value, list) else [value]
    return normalized


def summarize_tuning(tuning: dict[str, list]) -> dict[str, int | bool]:
    counts = {key: len(value) for key, value in tuning.items()}
    counts["has_pending_tuning"] = any(counts[key] > 0 for key in tuning)
    return counts


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    latest_decision = read_json(lgwf_dir / "composition_plan_decision.json")
    confirmed_plan = read_json(lgwf_dir / "confirmed_composition_plan.json")
    pending_tuning = normalize_tuning(latest_decision.get("tuning"))
    context = {
        "request": read_json(lgwf_dir / "lgwf_wf_thinking_request.json"),
        "available_workflows": read_json(lgwf_dir / "available_workflows.json"),
        "classification": read_json(lgwf_dir / "need_classification.json"),
        "composition_plan": read_json(lgwf_dir / "composition_plan.json"),
        "instruction": "请确认、微调或拒绝组合方案。确认后将生成 handoff 指令，不直接执行下游 workflow。",
    }
    if latest_decision:
        context["latest_decision"] = latest_decision
        context["revision_summary"] = summarize_tuning(pending_tuning)
        if latest_decision.get("decision") == "revise" or context["revision_summary"]["has_pending_tuning"]:
            context["pending_tuning"] = pending_tuning
    confirmed_tuning = normalize_tuning(confirmed_plan.get("tuning"))
    if confirmed_plan:
        context["confirmed_plan_history"] = {
            "status": confirmed_plan.get("status", ""),
            "has_tuning": any(confirmed_tuning[key] for key in confirmed_tuning),
            "tuning": confirmed_tuning,
        }
    (lgwf_dir / "confirm_plan_context.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_wf_thinking.confirm_context": context}, ensure_ascii=False))


if __name__ == "__main__":
    main()
