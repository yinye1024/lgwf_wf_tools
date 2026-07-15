"""根据步骤设计 observation 确定性写入 ReAct route 决策。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_value(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def stable_json_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def issue_signatures(observation: dict[str, Any]) -> list[str]:
    signatures: list[str] = []
    for item in list_value(observation, "issue_signatures"):
        text = str(item).strip()
        if text and text not in signatures:
            signatures.append(text)
    for item in list_value(observation, "blocking_issues"):
        if not isinstance(item, dict):
            continue
        text = str(item.get("issue_id") or item.get("target_path") or item.get("evidence") or "").strip()
        if text and text not in signatures:
            signatures.append(text)
    for item in list_value(observation, "failed_checks"):
        if not isinstance(item, dict):
            continue
        text = str(item.get("name") or item.get("message") or "").strip()
        if text and text not in signatures:
            signatures.append(text)
    return signatures


def reason_feedback(observation: dict[str, Any], repeated: list[str]) -> dict[str, Any]:
    feedback = observation.get("reason_feedback")
    result = feedback if isinstance(feedback, dict) else {}
    result = dict(result)
    result["repeat_issue_signatures"] = repeated
    if repeated:
        result["act_instruction_patch"] = [
            {
                "issue_id": signature,
                "instruction": "该问题已重复出现；下一轮 REASON 必须给出更具体的字段级修复方案。",
            }
            for signature in repeated
        ]
    return result


def build_analysis(observation: dict[str, Any], previous_decision: dict[str, Any], proposal_hash: str) -> dict[str, Any]:
    passed = observation.get("passed") is True
    signatures = issue_signatures(observation)
    previous_hash = str(previous_decision.get("proposal_hash", "")).strip()
    previous_source = str(previous_decision.get("source", "")).strip()
    previous_signatures = set()
    if previous_source == "python_decide_step_designs" and previous_hash == proposal_hash:
        previous_signatures = {str(item).strip() for item in list_value(previous_decision, "issue_signatures") if str(item).strip()}
    repeated = [signature for signature in signatures if signature in previous_signatures]
    return {
        "recommended_next": "exit" if passed else "continue",
        "reason": "step designs observation passed" if passed else "step designs observation still has blocking issues",
        "issue_signatures": signatures,
        "repeat_issue_signatures": repeated,
        "no_progress_risk": bool(repeated and not passed),
        "next_reason_feedback": reason_feedback(observation, repeated),
        "source": "python_decide_step_designs",
        "proposal_hash": proposal_hash,
    }


def decide(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    observation = read_json(lgwf_dir / "step_design_observation.json")
    previous_decision = read_json(lgwf_dir / "step_designs_proposal_decision.json")
    proposal_hash = str(observation.get("proposal_hash", "")).strip()
    if not proposal_hash:
        proposal_hash = stable_json_hash(read_json(lgwf_dir / "step_designs_proposal.json"))
    analysis = build_analysis(observation, previous_decision, proposal_hash)
    passed = observation.get("passed") is True
    next_value = "exit" if passed else "continue"
    result = {
        "next": next_value,
        "passed": passed,
        "reason": analysis["reason"],
        "recommended_next": analysis.get("recommended_next", ""),
        "issue_signatures": analysis["issue_signatures"],
        "repeat_issue_signatures": list_value(analysis, "repeat_issue_signatures"),
        "no_progress_risk": analysis.get("no_progress_risk") is True,
        "next_reason_feedback": analysis.get("next_reason_feedback", {}),
        "observation_file": ".lgwf/step_design_observation.json",
        "decision_analysis_file": ".lgwf/step_design_decision_analysis.json",
        "source": "python_decide_step_designs",
        "proposal_hash": proposal_hash,
    }
    write_json(lgwf_dir / "step_design_decision_analysis.json", analysis)
    write_json(lgwf_dir / "step_designs_proposal_decision.json", result)
    return result


def main() -> None:
    result = decide(Path.cwd())
    print(
        json.dumps(
            {
                "next": result["next"],
                "lgwf_wf_create.step_designs_proposal_decision": result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
