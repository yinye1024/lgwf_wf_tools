from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LGWF_DIR = Path(".lgwf")

ARTIFACTS = {
    "script_flow": ("e2e_script_flow_generation.json", "e2e_script_flow_observe.json"),
    "runtime_fake": ("e2e_runtime_fake_generation.json", "e2e_runtime_fake_observe.json"),
    "real_positive": ("e2e_real_positive_generation.json", "e2e_real_positive_observe.json"),
    "wf_fix_positive": ("e2e_wf_fix_positive_generation.json", "e2e_wf_fix_positive_observe.json"),
}


def read_request() -> dict[str, Any]:
    return json.loads((LGWF_DIR / "e2e_target_request.normalized.json").read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_skip_artifacts(test_type: str, request: dict[str, Any]) -> None:
    generation_name, observe_name = ARTIFACTS[test_type]
    generated_tests = request.get("generated_tests") or {}
    reason = f"{test_type} 未被 selected_test_types 选中，按路由跳过。"
    generation = {
        "status": "skipped",
        "passed": False,
        "generated": False,
        "test_type": test_type,
        "test_file": generated_tests.get(test_type, ""),
        "reason": reason,
        "notes": [reason],
    }
    observe = {
        "status": "skipped",
        "passed": False,
        "test_type": test_type,
        "issues": [],
        "summary": reason,
        "commands": [],
        "coverage_gaps": [],
    }
    write_json(LGWF_DIR / generation_name, generation)
    write_json(LGWF_DIR / observe_name, observe)


def route_payload(node_id: str, test_type: str) -> dict[str, Any]:
    request = read_request()
    selected = set(request.get("selected_test_types") or [])
    next_route = "run" if test_type in selected else "skip"
    if next_route == "skip":
        write_skip_artifacts(test_type, request)
    return {
        f"__route__{node_id}": next_route,
        "next": next_route,
        "selected": next_route == "run",
    }
