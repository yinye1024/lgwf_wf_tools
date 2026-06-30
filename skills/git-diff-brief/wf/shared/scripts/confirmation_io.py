"""确认类节点的通用 JSON、路径和 decision 校验工具。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


def normalize_relative_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute():
        raise ValueError(f"{field_name} 禁止绝对路径")
    if ":" in cleaned:
        raise ValueError(f"{field_name} 禁止盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止写入目标 package 根目录 `.lgwf`")
    normalized = candidate.as_posix().strip("/")
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
