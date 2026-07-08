"""同步原始意图产物到 state，并结束该阶段。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_raw_intent_request(root: Path) -> dict:
    path = root / ".lgwf" / "raw_intent_request.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
        return result
    return []


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def creation_context_targets(raw_intent_request: dict) -> tuple[list[str], list[str]]:
    request = raw_intent_request.get("request")
    if not isinstance(request, dict):
        request = {}

    dirs = []
    dirs.extend(_as_string_list(raw_intent_request.get("creation_context_dirs")))
    dirs.extend(_as_string_list(request.get("target_dir")))
    dirs.extend(_as_string_list(request.get("target_dirs")))

    files = []
    files.extend(_as_string_list(raw_intent_request.get("creation_context_files")))
    files.extend(_as_string_list(request.get("target_file")))
    files.extend(_as_string_list(request.get("target_files")))

    return _dedupe(dirs), _dedupe(files)


def main() -> None:
    raw_intent_request = load_raw_intent_request(Path.cwd())
    creation_context_dirs, creation_context_files = creation_context_targets(raw_intent_request)
    print(
        json.dumps(
            {
                "lgwf_wf_create.raw_intent_request": raw_intent_request,
                "lgwf_wf_create.creation_context_dirs": creation_context_dirs,
                "lgwf_wf_create.creation_context_files": creation_context_files,
                "lgwf_wf_create.raw_intent_finished": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
