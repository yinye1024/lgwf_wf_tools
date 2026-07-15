"""根据修复 observe 结果决定 ReAct 是否继续。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def failure_signatures(source: dict[str, Any]) -> list[str]:
    signatures: list[str] = []
    raw_failures = source.get("failures", [])
    if isinstance(raw_failures, list):
        for item in raw_failures:
            text = str(item).strip()
            if text and text not in signatures:
                signatures.append(text)
    raw_checks = source.get("checks", [])
    if isinstance(raw_checks, list):
        for item in raw_checks:
            if not isinstance(item, dict) or item.get("ok") is not False:
                continue
            label = str(item.get("check", "")).strip()
            path = str(item.get("path", "")).strip()
            signature = f"{label}: {path}".strip(": ")
            if signature and signature not in signatures:
                signatures.append(signature)
    audit = source.get("audit", {})
    if isinstance(audit, dict) and audit.get("ok") is False:
        stderr = str(audit.get("stderr", "")).strip()
        if stderr:
            first_line = stderr.splitlines()[0].strip()
            if first_line and first_line not in signatures:
                signatures.append(first_line)
    return signatures[:20]


def build_analysis(source: dict[str, Any], passed: bool) -> dict[str, Any]:
    signatures = failure_signatures(source)
    return {
        "recommended_next": "exit" if passed else "continue",
        "reason": "authoring audit passed" if passed else "authoring audit failed; continue implementation repair",
        "failure_signatures": signatures,
        "repeat_issue_signatures": [],
        "no_progress_risk": False,
    }


def decide(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    audit = read_json(lgwf_dir / "implementation_audit_result.json")
    observe = read_json(lgwf_dir / "implementation_observe.json")
    source = audit if audit else observe
    passed = source.get("passed") is True and not bool(source.get("needs_post_fix"))
    analysis = build_analysis(source, passed)
    result = {
        "next": "exit" if passed else "continue",
        "passed": passed,
        "reason": analysis["reason"],
        "source": "implementation_audit_result.json" if audit else "implementation_observe.json",
        "status": source.get("status", "passed" if passed else "failed"),
        "needs_post_fix": bool(source.get("needs_post_fix")),
        "failures": source.get("failures", []),
        "decision_analysis": analysis,
    }
    write_json(lgwf_dir / "implementation_repair_decision_analysis.json", analysis)
    write_json(lgwf_dir / "implementation_decision.json", result)
    return result


def main() -> None:
    result = decide(Path.cwd())
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
