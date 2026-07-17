from __future__ import annotations

import json
from pathlib import Path
from typing import Any


KEYWORDS = {
    "create": ["创建", "新建", "生成", "create", "build", "scaffold"],
    "fix": ["修复", "报错", "失败", "debug", "fix", "repair", "broken"],
    "convert": ["转换", "迁移", "改造成", "convert", "migrate", "transform"],
    "optimize": ["优化", "升级", "改进", "重构", "optimize", "upgrade", "improve"],
    "test": ["测试", "e2e", "验收", "test", "coverage"],
    "prompt": ["prompt", "提示词", "agent"],
    "governance": ["规范", "治理", "审计", "质量", "governance", "audit"],
}

WORKFLOW_HINTS = {
    "create": ["wf-create-fast"],
    "fix": ["wf-fix"],
    "convert": ["wf-convert"],
    "optimize": ["wf-prompt-upgrade", "wf-prompt-fix"],
    "test": ["e2e-test-generator"],
    "prompt": ["wf-prompt-fix", "wf-prompt-upgrade"],
    "governance": ["self-improve", "e2e-test-generator"],
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    cwd = Path.cwd()
    lgwf_dir = cwd / ".lgwf"
    request = read_json(lgwf_dir / "lgwf_wf_thinking_request.json")
    registry = read_json(lgwf_dir / "available_workflows.json")
    text = str(request.get("raw_intent", "")).lower()

    matched_types = [
        need_type
        for need_type, words in KEYWORDS.items()
        if any(word.lower() in text for word in words)
    ]
    if not matched_types:
        matched_types = ["optimize"]

    available_ids = {
        str(item.get("id") or item.get("name"))
        for item in registry.get("workflows", [])
        if item.get("id") or item.get("name")
    }
    recommended: list[str] = []
    missing: list[str] = []
    for need_type in matched_types:
        for workflow_id in WORKFLOW_HINTS.get(need_type, []):
            if workflow_id in available_ids and workflow_id not in recommended:
                recommended.append(workflow_id)
            elif workflow_id not in available_ids and workflow_id not in missing:
                missing.append(workflow_id)

    result = {
        "need_types": matched_types,
        "primary_need_type": matched_types[0],
        "recommended_workflows": recommended,
        "missing_expected_workflows": missing,
        "requires_user_confirmation": True,
        "handoff_required": True,
    }
    (lgwf_dir / "need_classification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_wf_thinking.classification": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
