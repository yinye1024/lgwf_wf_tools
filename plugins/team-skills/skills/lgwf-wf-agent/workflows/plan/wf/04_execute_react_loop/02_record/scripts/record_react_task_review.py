from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_manager():
    path = Path(__file__).resolve().parents[2] / "00_prepare" / "scripts" / "manage_react_task.py"
    spec = importlib.util.spec_from_file_location("manage_react_task", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def validate_result(result: dict) -> None:
    if result.get("verdict") not in {"pass", "fail", "blocked"}:
        raise SystemExit("react_task_result.verdict must be pass, fail, or blocked")
    passed = result.get("pass") is True or result.get("verdict") == "pass"
    if passed:
        if result.get("required_follow_up"):
            raise SystemExit("pass result requires empty required_follow_up")
        for key in ("evidence", "accepted"):
            if key not in result or result.get(key) in (None, [], False):
                raise SystemExit(f"pass result requires non-empty {key}")
        for key in (
            "criteria_results",
            "required_check_results",
            "negative_check_results",
            "risk_check_results",
            "plan_validation_results",
        ):
            if not result.get(key):
                raise SystemExit(f"pass result requires non-empty {key}")
        scope = result.get("scope_compliance")
        if isinstance(scope, dict) and (scope.get("within_scope") is not True or scope.get("issues")):
            raise SystemExit("pass result requires scope_compliance.within_scope=true and empty issues")
    else:
        if not result.get("required_follow_up"):
            raise SystemExit("failed result requires non-empty required_follow_up")


def main() -> None:
    root = Path.cwd()
    context = load(root / ".lgwf" / "react_task_context.json")
    if context.get("all_done") is True:
        print(json.dumps({"lgwf_plan.react_task_route": {"route": "all_done"}}, ensure_ascii=False))
        return
    task_id = (context.get("task") or {}).get("task_id")
    if not task_id:
        raise SystemExit("current task_id missing")
    result = load(root / ".lgwf" / "react_task_result.json")
    validate_result(result)
    route = load_manager().record_review(root, task_id, result, max_attempts=int(context.get("max_attempts") or 3))
    print(json.dumps({"lgwf_plan.react_task_route": route}, ensure_ascii=False))


if __name__ == "__main__":
    main()
