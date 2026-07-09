"""共享的确认记录读写 helper。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_relative_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute() or ":" in cleaned:
        raise ValueError(f"{field_name} 禁止绝对路径或盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    return candidate.as_posix().strip("/")


def unwrap_approval(payload: dict[str, Any], label: str) -> dict[str, Any]:
    if not payload:
        raise ValueError(f"{label} 不能为空")
    approval = str(payload.get("approval", "")).strip()
    if approval not in {"approve", "revise", "reject"}:
        raise ValueError(f"{label}.approval 非法: {approval!r}")
    return payload


def confirmed_from_proposal(lgwf_dir: Path, approval: dict[str, Any], proposal_file: str) -> dict[str, Any]:
    if str(approval.get("approval", "")).strip() != "approve":
        raise ValueError("只有 approve 才能固化 confirmed artifact")
    proposal = load_json(lgwf_dir / proposal_file)
    if not proposal:
        raise FileNotFoundError(f"找不到 proposal: {proposal_file}")
    return proposal
