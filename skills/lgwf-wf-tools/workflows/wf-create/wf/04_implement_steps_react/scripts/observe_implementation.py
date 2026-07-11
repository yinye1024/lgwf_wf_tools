"""把确定性 audit 结果发布为 implementation observe 反馈。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit_diagnostics(audit: dict[str, Any]) -> list[str]:
    stdout = str(audit.get("stdout", "")).strip()
    if not stdout:
        return []
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        return []
    result: list[str] = []
    for item in diagnostics:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).strip()
        message = str(item.get("message", "")).strip()
        suggestion = str(item.get("suggestion", "")).strip()
        location = str(item.get("location", "")).strip()
        parts = [part for part in (code, message, suggestion, location) if part]
        if parts:
            result.append(" | ".join(parts))
    return result


def build_observe(work_dir: Path) -> dict[str, Any]:
    audit_result = load_json(work_dir / ".lgwf" / "implementation_audit_result.json")
    if not audit_result:
        raise FileNotFoundError("缺少 .lgwf/implementation_audit_result.json")
    audit = audit_result.get("audit")
    if not isinstance(audit, dict):
        audit = {}
    failures = [
        str(item)
        for item in audit_result.get("failures", [])
        if isinstance(audit_result.get("failures", []), list) and str(item).strip()
    ]
    failures.extend(audit_diagnostics(audit))
    deduped_failures = list(dict.fromkeys(failures))
    passed = audit_result.get("passed") is True and audit.get("ok") is True
    observe = dict(audit_result)
    observe["passed"] = passed
    observe["failures"] = deduped_failures
    observe["next_action_hint"] = [] if passed else deduped_failures
    observe["summary"] = (
        "authoring audit passed; implementation can exit"
        if passed
        else "authoring audit failed; feed diagnostics into the next ACT repair round"
    )
    write_json(work_dir / ".lgwf" / "implementation_observe.json", observe)
    return observe


def main() -> None:
    observe = build_observe(Path.cwd())
    print(
        json.dumps(
            {"lgwf_wf_create.implementation_observe_result": observe},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
