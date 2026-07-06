from __future__ import annotations

import json
from datetime import datetime, timezone

from _paths import LOCAL_SELF_IMPROVE, SELF_IMPROVE_ROOT, WORKFLOW_ROOT


def main() -> int:
    checks = [
        {"label": "manifest_exists", "passed": (SELF_IMPROVE_ROOT / "manifest.json").is_file()},
        {"label": "agents_exists", "passed": (WORKFLOW_ROOT / "AGENTS.md").is_file()},
        {"label": "baseline_cases_exists", "passed": (SELF_IMPROVE_ROOT / "evals" / "baseline-cases.json").is_file()},
        {"label": "entrypoint_exists", "passed": (SELF_IMPROVE_ROOT / "scripts" / "self_improve.py").is_file()},
        {"label": "trace_eval_exists", "passed": (SELF_IMPROVE_ROOT / "scripts" / "run_trace_eval.py").is_file()},
        {"label": "check_exists", "passed": (SELF_IMPROVE_ROOT / "scripts" / "check_self_improve.py").is_file()},
    ]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    output = LOCAL_SELF_IMPROVE / "reports" / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-self-eval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "report": str(output)}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
