from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def unwrap_review_value(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("value")
    if isinstance(value, dict):
        payload = value
    confirmed = payload.get("confirmed")
    if isinstance(confirmed, dict):
        payload = confirmed
    nested = payload.get("prompt_convert_target")
    if isinstance(nested, dict):
        payload = nested
    if not isinstance(payload.get("target_dir"), str) or not payload["target_dir"].strip():
        raise ValueError("prompt_convert_target 缺少非空 target_dir")
    return payload


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    approval = read_json(lgwf_dir / "prompt_convert_target_approval.json")
    try:
        target = unwrap_review_value(approval)
    except ValueError:
        target = read_json(lgwf_dir / "prompt_convert_target_proposal.json")
        target = unwrap_review_value(target)
    output_path = lgwf_dir / "prompt_convert_target.json"
    output_path.write_text(json.dumps(target, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"lgwf_wf_convert.prompt_convert_target": target}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
