from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from dsl_upgrade_common import compute_sha256, ensure_runtime_dirs, path_is_authorized, unique_strings, write_json


def _is_runtime_state_path(path: Path) -> bool:
    return ".lgwf" in path.parts


def _append_unique_candidate(candidates: list[dict[str, str]], seen: set[str], raw_path: str, resolved: Path) -> None:
    key = str(resolved)
    if key in seen:
        return
    seen.add(key)
    candidates.append({"raw_path": raw_path, "resolved_path": key})


def _normalize_request(raw_request: dict[str, Any]) -> dict[str, Any]:
    target_paths = raw_request.get("target_paths", [])
    allowed_dirs = raw_request.get("allowed_dirs", [])
    if not isinstance(target_paths, list):
        raise TypeError("target_paths 必须是字符串数组")
    if not isinstance(allowed_dirs, list):
        raise TypeError("allowed_dirs 必须是字符串数组")
    return {
        "target_paths": [str(item).strip() for item in target_paths if str(item).strip()],
        "allowed_dirs": [str(item).strip() for item in allowed_dirs if str(item).strip()],
        "mode": str(raw_request.get("mode", "dry_run")).strip() or "dry_run",
        "scope_mode": str(raw_request.get("scope_mode", "explicit")).strip() or "explicit",
        "max_targets": int(raw_request.get("max_targets", 8) or 8),
    }


def unwrap_audit_fix_target(raw_request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw_request, dict):
        raise TypeError("audit_fix_target 输入必须是 JSON object")
    wrapped = raw_request.get("audit_fix_target")
    if isinstance(wrapped, dict):
        return wrapped
    legacy_wrapped = raw_request.get("dsl_upgrade_target")
    if isinstance(legacy_wrapped, dict):
        return legacy_wrapped
    return raw_request


def collect_targets_from_request(root: Path, raw_request: dict[str, Any]) -> dict[str, Any]:
    _, _ = ensure_runtime_dirs(root)
    request = _normalize_request(unwrap_audit_fix_target(raw_request))
    validation_reasons: list[str] = []
    targets: list[dict[str, Any]] = []
    mode = request["mode"]
    scope_mode = request["scope_mode"]
    max_targets = request["max_targets"]
    allowed_paths: list[Path] = []

    if mode not in {"dry_run", "apply"}:
        validation_reasons.append(f"不支持的 mode: {mode}")
    if scope_mode not in {"explicit", "registry"}:
        validation_reasons.append(f"不支持的 scope_mode: {scope_mode}")
    if max_targets < 1:
        validation_reasons.append("max_targets 必须大于 0")
    for raw_dir in request["allowed_dirs"]:
        candidate = Path(raw_dir).expanduser().resolve()
        if not candidate.exists() or not candidate.is_dir():
            validation_reasons.append(f"allowed_dirs 不存在或不是目录: {raw_dir}")
            continue
        allowed_paths.append(candidate)
    if not allowed_paths:
        validation_reasons.append("缺少可用的 allowed_dirs，无法建立授权边界")
    if mode == "apply" and not request["allowed_dirs"]:
        validation_reasons.append("mode=apply 时必须提供 allowed_dirs")

    if scope_mode == "registry":
        validation_reasons.append("scope_mode=registry 当前只保留契约，尚未实现真实解析")
    else:
        if not request["target_paths"]:
            validation_reasons.append("scope_mode=explicit 时必须提供 target_paths")
        target_candidates: list[dict[str, str]] = []
        seen_candidates: set[str] = set()
        for raw_path in request["target_paths"]:
            input_path = Path(raw_path).expanduser().resolve()
            if not input_path.exists():
                _append_unique_candidate(target_candidates, seen_candidates, raw_path, input_path)
                continue
            if input_path.is_dir():
                discovered = sorted(
                    item.resolve()
                    for item in input_path.rglob("*.lgwf")
                    if item.is_file() and not _is_runtime_state_path(item)
                )
                if not discovered:
                    validation_reasons.append(f"目录内未发现 .lgwf 文件: {raw_path}")
                for discovered_path in discovered:
                    _append_unique_candidate(target_candidates, seen_candidates, raw_path, discovered_path)
                continue
            _append_unique_candidate(target_candidates, seen_candidates, raw_path, input_path)
        if len(target_candidates) > max_targets:
            validation_reasons.append(f"目标数量超过 max_targets={max_targets}")
        for candidate in target_candidates[:max_targets]:
            raw_path = candidate["raw_path"]
            resolved = Path(candidate["resolved_path"])
            target_reasons: list[str] = []
            exists = resolved.exists()
            is_workflow = exists and resolved.is_file() and resolved.suffix.lower() == ".lgwf"
            if not exists:
                target_reasons.append("目标不存在")
            if exists and not is_workflow:
                target_reasons.append("目标必须是 .lgwf 文件或包含 .lgwf 文件的目录")
            authorized = exists and is_workflow and bool(allowed_paths) and path_is_authorized(resolved, allowed_paths)
            if exists and allowed_paths and not path_is_authorized(resolved, allowed_paths):
                target_reasons.append("目标超出 allowed_dirs")
            if exists and is_workflow and not allowed_paths:
                target_reasons.append("缺少 allowed_dirs，无法确认授权")
            targets.append(
                {
                    "raw_path": raw_path,
                    "resolved_path": str(resolved),
                    "exists": exists,
                    "is_workflow": is_workflow,
                    "authorized": authorized,
                    "reasons": target_reasons,
                    "pre_hash": compute_sha256(resolved) if exists and is_workflow else None,
                }
            )

    authorized_targets = [item for item in targets if item.get("authorized")]
    per_target_reasons = [reason for item in targets for reason in item.get("reasons", [])]
    validation = {
        "passed": not validation_reasons and bool(targets) and len(authorized_targets) == len(targets),
        "reasons": unique_strings([*validation_reasons, *per_target_reasons]),
        "target_count": len(targets),
        "authorized_count": len(authorized_targets),
        "mode": mode,
        "scope_mode": scope_mode,
    }
    manifest = {
        "request": request,
        "targets": targets,
        "authorized_targets": authorized_targets,
        "target_count": len(targets),
        "validation": validation,
    }
    foreach_targets = build_foreach_targets(request, authorized_targets, allowed_paths)
    state_updates = {
        "wf_audit_fix.targets": foreach_targets,
        "wf_audit_fix.collect_targets_result": {
            "validation": validation,
            "target_count": len(targets),
            "authorized_count": len(authorized_targets),
        },
    }
    write_json(root / ".lgwf" / "target_manifest.json", manifest)
    write_json(root / ".lgwf" / "target_scope_validation.json", validation)
    return {
        "request": request,
        "manifest": manifest,
        "validation": validation,
        "state_updates": state_updates,
    }


def build_foreach_targets(
    request: dict[str, Any],
    authorized_targets: list[dict[str, Any]],
    allowed_paths: list[Path],
) -> list[dict[str, Any]]:
    allowed_dirs = [str(path.resolve()) for path in allowed_paths]
    foreach_targets: list[dict[str, Any]] = []
    for index, target in enumerate(authorized_targets, start=1):
        target_path = Path(str(target["resolved_path"])).resolve()
        foreach_targets.append(
            {
                "target_id": f"target_{index:04d}",
                "raw_path": str(target.get("raw_path", "")),
                "path": str(target_path),
                "target_files": [str(target_path)],
                "target_dirs": [str(target_path.parent.resolve())],
                "allowed_dirs": allowed_dirs,
                "mode": request["mode"],
                "scope_mode": request["scope_mode"],
                "authorized": bool(target.get("authorized")),
                "pre_hash": target.get("pre_hash"),
            }
        )
    return foreach_targets


def main() -> None:
    root = Path.cwd()
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    request = json.loads(raw) if raw else {}
    result = collect_targets_from_request(root, request if isinstance(request, dict) else {})
    print(json.dumps(result["state_updates"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
