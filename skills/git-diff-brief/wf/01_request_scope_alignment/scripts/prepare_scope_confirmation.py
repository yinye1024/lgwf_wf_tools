from __future__ import annotations

import json
from pathlib import Path


def load_capture(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "repository_input_context": {},
            "summary_scope": {},
            "scope_confirmation_input": {
                "needs_confirmation": True,
                "open_questions": ["缺少 request_scope_capture.json，需补齐第一阶段输出。"],
                "recommended_decision": "revise",
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    capture = load_capture(Path(".lgwf/request_scope_capture.json"))
    payload = {
        "git_diff_brief.repository_input_context": capture.get("repository_input_context", {}),
        "git_diff_brief.summary_scope": capture.get("summary_scope", {}),
        "git_diff_brief.scope_confirmation_input": capture.get("scope_confirmation_input", {}),
        "git_diff_brief.prepare_scope_confirmation_result": {
            "ok": True,
            "source_file": ".lgwf/request_scope_capture.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
