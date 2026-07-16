from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_FIELDS = (
    "workflow_name",
    "target_package_root",
    "raw_intent",
    "source_root",
    "stages",
    "prompt_contracts",
    "source_business_contract",
    "prompt_execution_mechanics",
    "presentation_constraints",
    "discarded_prompt_techniques",
    "conversion_mapping",
    "parity_requirements",
    "human_approval_points",
    "assumptions",
    "out_of_scope",
    "run_workflow_notes_for_wf_create_fast",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def has_valid_target_package_root(value: Any) -> bool:
    raw = str(value or "").strip()
    candidate = PurePosixPath(raw.replace("\\", "/"))
    if not raw or raw == ".":
        return False
    if candidate.is_absolute():
        return False
    if ":" in raw:
        return False
    if any(part == ".." for part in candidate.parts):
        return False
    if any(part == ".lgwf" for part in candidate.parts):
        return False
    return True


def has_required_payload_shape(proposal: dict[str, Any]) -> bool:
    if not all(field in proposal for field in REQUIRED_FIELDS):
        return False
    if not str(proposal.get("workflow_name", "")).strip():
        return False
    if not str(proposal.get("raw_intent", "")).strip():
        return False
    if not str(proposal.get("source_root", "")).strip():
        return False
    return has_valid_target_package_root(proposal.get("target_package_root"))


def has_blocking_issue(observe: dict[str, Any]) -> bool:
    issues = observe.get("issues", [])
    if not isinstance(issues, list):
        return True
    for issue in issues:
        if not isinstance(issue, dict):
            return True
        if issue.get("blocking") is True:
            return True
        if "blocking" not in issue and observe.get("verdict") != "pass":
            return True
    return False


def decide_next(proposal: dict[str, Any], observe: dict[str, Any]) -> str:
    if not has_required_payload_shape(proposal):
        return "continue"
    if observe.get("verdict") == "pass":
        return "exit"
    if has_blocking_issue(observe):
        return "continue"
    return "exit"


def main() -> None:
    root = Path.cwd()
    proposal = load_json(root / ".lgwf" / "wf_create_fast_input_proposal.json")
    observe = load_json(root / ".lgwf" / "wf_create_fast_input_observe.json")
    print(json.dumps({"next": decide_next(proposal, observe)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

