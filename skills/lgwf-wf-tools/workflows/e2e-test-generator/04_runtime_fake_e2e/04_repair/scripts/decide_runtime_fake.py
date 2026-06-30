from __future__ import annotations

from pathlib import Path
import hashlib
import json
from typing import Any


OBSERVE_PATH = Path(".lgwf/e2e_runtime_fake_observe.json")
REPAIR_CONTEXT_PATH = Path(".lgwf/e2e_runtime_fake_repair_context.json")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def collect_blockers(data: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for key, check in sorted((data.get("contract_checks") or {}).items()):
        if isinstance(check, dict) and not bool(check.get("passed")):
            issue_code = normalize_text(check.get("issue_code")) or f"contract:{key}"
            blockers.append(
                {
                    "issue_code": issue_code,
                    "source": "contract_checks",
                    "target": key,
                    "evidence": normalize_text(check.get("evidence")),
                    "source_location": normalize_text(check.get("source_location")),
                    "repair_hint": normalize_text(check.get("repair_hint")),
                }
            )
    for key, check in sorted((data.get("scenario_checks") or {}).items()):
        if isinstance(check, dict) and not bool(check.get("passed")):
            issue_code = normalize_text(check.get("issue_code")) or f"scenario:{key}"
            blockers.append(
                {
                    "issue_code": issue_code,
                    "source": "scenario_checks",
                    "target": key,
                    "evidence": normalize_text(check.get("evidence")),
                    "source_location": normalize_text(check.get("source_location")),
                    "repair_hint": normalize_text(check.get("repair_hint")),
                }
            )
    for gap in data.get("coverage_gaps") or []:
        if isinstance(gap, dict) and bool(gap.get("blocking")):
            target = normalize_text(gap.get("target"))
            blockers.append(
                {
                    "issue_code": f"coverage:{normalize_text(gap.get('kind'))}:{target}",
                    "source": "coverage_gaps",
                    "target": target,
                    "evidence": normalize_text(gap.get("reason")),
                    "source_location": "",
                    "repair_hint": "补齐该 blocking coverage gap，或在设计 JSON 中给出稳定且可验收的跳过理由。",
                }
            )
    if not blockers:
        for index, issue in enumerate(data.get("issues") or []):
            text = normalize_text(issue)
            if text:
                blockers.append(
                    {
                        "issue_code": f"issue:{index}",
                        "source": "issues",
                        "target": text[:80],
                        "evidence": text,
                        "source_location": "",
                        "repair_hint": "",
                    }
                )
    return blockers


def signature_for(blockers: list[dict[str, Any]]) -> str:
    stable = [
        {
            "issue_code": blocker.get("issue_code", ""),
            "target": blocker.get("target", ""),
            "repair_hint": blocker.get("repair_hint", ""),
        }
        for blocker in blockers
    ]
    payload = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def main() -> None:
    if not OBSERVE_PATH.exists():
        context = {
            "active": True,
            "attempt": 1,
            "blockers": [
                {
                    "issue_code": "observe:missing_output",
                    "source": "decide",
                    "target": str(OBSERVE_PATH),
                    "evidence": "缺少 observe 输出，无法验收 runtime fake E2E。",
                    "source_location": str(OBSERVE_PATH),
                    "repair_hint": "先确保 observe 阶段写出严格 JSON object。",
                }
            ],
            "issue_signature": "observe_missing_output",
            "previous_signatures": [],
            "no_progress": False,
            "instructions": [
                "下一轮 reason/act 必须优先修复 blockers，不得重新扩大设计范围。",
            ],
        }
        write_json(REPAIR_CONTEXT_PATH, context)
        print(json.dumps({"next": "continue", "lgwf_e2e.runtime_fake_validation": {"passed": False, "reason": "missing observe output"}, "lgwf_e2e.runtime_fake_repair_context": context}, ensure_ascii=False))
        return

    data = read_json(OBSERVE_PATH, {})
    passed = bool(data.get("passed"))
    previous = read_json(REPAIR_CONTEXT_PATH, {})
    previous_signatures = list(previous.get("previous_signatures") or [])

    if passed:
        context = {
            "active": False,
            "attempt": int(previous.get("attempt") or 0),
            "blockers": [],
            "issue_signature": "",
            "previous_signatures": previous_signatures,
            "no_progress": False,
            "instructions": ["runtime fake E2E observe 已通过，退出 REACT。"],
        }
        write_json(REPAIR_CONTEXT_PATH, context)
        print(json.dumps({"next": "exit", "lgwf_e2e.runtime_fake_validation": data, "lgwf_e2e.runtime_fake_repair_context": context}, ensure_ascii=False))
        return

    blockers = collect_blockers(data)
    signature = signature_for(blockers)
    repeated = signature in previous_signatures or signature == previous.get("issue_signature")
    attempt = int(previous.get("attempt") or 0) + 1
    context = {
        "active": True,
        "attempt": attempt,
        "blockers": blockers,
        "issue_signature": signature,
        "previous_signatures": [*previous_signatures, signature],
        "no_progress": repeated,
        "instructions": [
            "下一轮 reason 必须把 blockers 转成 repair_plan，并禁止重新设计已通过部分。",
            "下一轮 act 只能修改 blockers 指向的失败点，并必须在 generation JSON 中记录 applied_repairs。",
            "如果同一 issue_signature 重复出现，停止 REACT 并报告 no_progress，避免继续消耗 token。",
        ],
    }
    write_json(REPAIR_CONTEXT_PATH, context)
    next_step = "exit" if repeated else "continue"
    result = dict(data)
    result["no_progress"] = repeated
    result["issue_signature"] = signature
    print(json.dumps({"next": next_step, "lgwf_e2e.runtime_fake_validation": result, "lgwf_e2e.runtime_fake_repair_context": context}, ensure_ascii=False))


if __name__ == "__main__":
    main()
