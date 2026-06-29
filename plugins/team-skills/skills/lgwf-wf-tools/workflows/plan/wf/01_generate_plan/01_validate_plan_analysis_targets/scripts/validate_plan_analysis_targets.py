from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing task request: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit("task request must be a JSON object")
    return data


def as_list(value: object) -> list:
    return value if isinstance(value, list) else []


def main() -> None:
    request_path = Path.cwd() / ".lgwf" / "react_task_request.json"
    request = read_json(request_path)
    issues: list[str] = []
    for key in ("objective", "request"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            issues.append(f"{key} is required")
    target_types = {"create_artifact", "modify_artifact", "execute_process", "analyze", "fix", "review"}
    target_type = str(request.get("target_type") or "").strip().lower()
    if target_type not in target_types:
        issues.append("target_type must be one of create_artifact, modify_artifact, execute_process, analyze, fix, review")
    files = as_list(request.get("analysis_target_files"))
    dirs = as_list(request.get("analysis_target_dirs"))
    if not files and not dirs:
        issues.append("analysis_target_files or analysis_target_dirs is required")
    result = {
        "lgwf_plan.plan_target_validation": {
            "passed": not issues,
            "issues": issues,
            "target_type": target_type,
            "analysis_target_files": files,
            "analysis_target_dirs": dirs,
        }
    }
    if issues:
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit("; ".join(issues))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

