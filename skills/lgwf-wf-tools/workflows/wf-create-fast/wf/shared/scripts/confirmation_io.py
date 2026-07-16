"""确认类节点的通用 JSON、路径和 approval 校验工具。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
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


def normalize_target_package_root(raw_path: str, field_name: str = "target_package_root") -> str:
    """规范化目标 package root。

    用户入口经常提供绝对路径；这里允许绝对路径和 workspace 相对路径，
    但仍禁止 URL、上跳路径和 `.lgwf` 运行态目录。
    """

    cleaned = raw_path.strip()
    if "://" in cleaned:
        raise ValueError(f"{field_name} 禁止 URL 路径")
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    parts = PureWindowsPath(cleaned).parts if ":" in cleaned else PurePosixPath(cleaned.replace("\\", "/")).parts
    if any(part == ".." for part in parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in parts):
        raise ValueError(f"{field_name} 禁止写入目标 package 根目录 `.lgwf`")
    return str(PureWindowsPath(cleaned)) if ":" in cleaned else PurePosixPath(cleaned.replace("\\", "/")).as_posix().rstrip("/")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def unwrap_approval(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get("value")
    if not isinstance(value, dict):
        value = payload
    if isinstance(value, dict):
        approval = value.get(key, value)
        if isinstance(approval, dict):
            return approval
    raise TypeError(f"{key} 必须是 JSON object")


def require_approve(approval: dict[str, Any]) -> None:
    if approval_decision(approval) != "approve":
        raise ValueError("只有 approval=approve 才能固化 confirmed artifact")


def approval_decision(approval: dict[str, Any]) -> str:
    raw_approval = approval.get("approval", approval.get("decision", approval.get("route", "")))
    if isinstance(raw_approval, dict):
        raw_approval = raw_approval.get("value", raw_approval.get("approval", raw_approval.get("decision", "")))
    return str(raw_approval).strip().lower()


def require_revise(approval: dict[str, Any]) -> None:
    if approval_decision(approval) != "revise":
        raise ValueError("只有 approval=revise 才能重写 proposal")


def revision_proposal_from_approval(approval: dict[str, Any]) -> dict[str, Any]:
    """从 REVIEW revise record 中提取完整修订后的 proposal。"""
    candidates: list[Any] = []
    value = approval.get("value")
    if isinstance(value, dict):
        candidates.extend(
            [
                value.get("proposal"),
                value.get("updated_proposal"),
                value.get("updated_context"),
                value.get("review_context_json"),
            ]
        )
    candidates.extend(
        [
            approval.get("proposal"),
            approval.get("updated_proposal"),
            approval.get("updated_context"),
            approval.get("review_context_json"),
        ]
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        proposal = candidate.get("proposal")
        if isinstance(proposal, dict) and proposal:
            return proposal
        if candidate:
            return candidate
    raise ValueError("revise 必须提交完整修订后的 proposal JSON")


def write_revised_proposal(
    *,
    lgwf_dir: Path,
    approval_file: str,
    approval_key: str,
    proposal_file: str,
    normalized_path_fields: tuple[str, ...] = (),
) -> dict[str, Any]:
    approval = unwrap_approval(load_json(lgwf_dir / approval_file), approval_key)
    require_revise(approval)
    proposal = revision_proposal_from_approval(approval)
    for field in normalized_path_fields:
        value = proposal.get(field)
        if isinstance(value, str) and value.strip():
            if field == "target_package_root":
                proposal[field] = normalize_target_package_root(value, field)
            else:
                proposal[field] = normalize_relative_path(value, field)
    write_json(lgwf_dir / proposal_file, proposal)
    return {
        "artifact_path": f".lgwf/{proposal_file}",
        "source_approval_file": f".lgwf/{approval_file}",
        "decision": "revise",
        "proposal": proposal,
    }


def confirmed_from_proposal(lgwf_dir: Path, approval: dict[str, Any], proposal_file: str) -> dict[str, Any]:
    """按固定 proposal 产物固化，不让 review value 承担业务结构生成职责。"""
    require_approve(approval)
    proposal = load_json(lgwf_dir / proposal_file)
    if not proposal:
        raise ValueError(f"{proposal_file} 不存在或为空，无法固化 confirmed artifact")
    return proposal


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
