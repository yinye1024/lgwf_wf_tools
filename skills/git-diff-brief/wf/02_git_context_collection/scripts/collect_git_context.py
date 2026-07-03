from __future__ import annotations

import json
import subprocess
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

DEFAULT_TOTAL_DIFF_BUDGET = 80_000
DEFAULT_FILE_DIFF_BUDGET = 8_000
HEAVY_SUFFIXES = {
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".pyc",
}
HEAVY_PATH_PARTS = {
    ".git",
    ".lgwf",
    "__pycache__",
    ".cache",
    "cache",
    "vendor",
    "node_modules",
    "dist",
    "build",
    "generated",
}


def normalize_repo_hint(raw: str) -> str:
    cleaned = str(raw or "").strip().rstrip("\\/")
    if not cleaned:
        return ""
    return PurePosixPath(cleaned.replace("\\", "/")).as_posix()


def repo_path_from_revision(path: Path = Path(".lgwf/request_scope_confirmation.json")) -> str:
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return ""
    value = data.get("value", data)
    if not isinstance(value, dict):
        return ""
    approval = str(value.get("approval", value.get("decision", ""))).strip().lower()
    if approval != "revise":
        return ""
    changes = value.get("changes", [])
    if isinstance(changes, list):
        for item in changes:
            if isinstance(item, dict) and str(item.get("field", "")).strip() in {"repo_path", "repo_hint", "repository"}:
                return normalize_repo_hint(str(item.get("value", "")))
            if isinstance(item, str):
                normalized = normalize_repo_hint(item)
                if normalized:
                    return normalized
    return ""


def repo_path_from_checkpoint(root: Path = Path(".lgwf/checkpoints")) -> str:
    if not root.exists():
        return ""
    checkpoints = sorted(root.glob("*/checkpoint.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in checkpoints:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            continue
        state = data.get("state_before_current_node", {})
        if not isinstance(state, dict):
            continue
        nested_input = state.get("input")
        source = nested_input if isinstance(nested_input, dict) else state
        repo_path = (
            source.get("repo_path")
            or source.get("repo_hint")
            or source.get("repository")
            or state.get("repo_path")
            or state.get("repo_hint")
            or state.get("repository")
        )
        normalized = normalize_repo_hint(str(repo_path or ""))
        if normalized:
            return normalized
    return ""


def repo_path_from_scope(path: Path = Path(".lgwf/request_scope_capture.json")) -> str:
    if not path.exists():
        return repo_path_from_revision() or repo_path_from_checkpoint() or "."
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        context = data.get("repository_input_context", {})
        if isinstance(context, dict):
            repo_path = context.get("normalized_repo_hint") or context.get("repo_hint")
            normalized = normalize_repo_hint(str(repo_path or ""))
            if normalized:
                return normalized
    return repo_path_from_revision() or repo_path_from_checkpoint() or "."


def build_changed_files_index(diff_names: list[str], status_lines: list[str]) -> dict[str, Any]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in [*diff_names, *status_lines]:
        value = str(raw).strip()
        if not value:
            continue
        if " " in value and not value.startswith(("docs/", "wf/", "src/", "tests/")):
            parts = value.split(maxsplit=1)
            path = parts[1].strip() if len(parts) == 2 else parts[0].strip()
        else:
            path = value
        if path and path not in seen:
            seen.add(path)
            ordered.append(path)
    return {"files": ordered, "count": len(ordered)}


def run_git(repo_path: str, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def split_lines(value: str) -> list[str]:
    return [line.rstrip() for line in value.splitlines() if line.strip()]


def first_path_segment(path: str) -> str:
    cleaned = str(path or "").strip().replace("\\", "/").strip("/")
    return cleaned.split("/", 1)[0] if cleaned else "."


def path_is_heavy(path: str) -> bool:
    normalized = str(path or "").replace("\\", "/").strip("/")
    parts = {part.lower() for part in normalized.split("/") if part}
    if parts.intersection(HEAVY_PATH_PARTS):
        return True
    return Path(normalized).suffix.lower() in HEAVY_SUFFIXES


def status_map_from_lines(status_lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in status_lines:
        if len(line) < 4:
            continue
        status = line[:2].strip() or line[:3].strip()
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[-1].strip()
        if path:
            result[path] = status
    return result


def split_diff_by_file(diff_text: str) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    current: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git ") and current:
            chunks.append(diff_chunk_to_record(current))
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append(diff_chunk_to_record(current))
    return [item for item in chunks if item.get("path")]


def diff_chunk_to_record(lines: list[str]) -> dict[str, str]:
    header = lines[0] if lines else ""
    path = ""
    if header.startswith("diff --git "):
        parts = header.split()
        if len(parts) >= 4:
            candidate = parts[3]
            path = candidate[2:] if candidate.startswith("b/") else candidate
    return {"path": path, "text": "\n".join(lines).rstrip()}


def build_directory_groups(files: list[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for path in files:
        grouped.setdefault(first_path_segment(path), []).append(path)
    return [
        {"directory": directory, "count": len(paths), "files": paths[:20], "truncated": len(paths) > 20}
        for directory, paths in sorted(grouped.items())
    ]


def build_diff_snippets(
    diff_text: str,
    status_lines: list[str],
    *,
    max_total_chars: int = DEFAULT_TOTAL_DIFF_BUDGET,
    max_file_chars: int = DEFAULT_FILE_DIFF_BUDGET,
) -> list[dict[str, Any]]:
    snippets: list[dict[str, Any]] = []
    used = 0
    status_by_path = status_map_from_lines(status_lines)
    for record in split_diff_by_file(diff_text):
        path = record["path"]
        text = record["text"]
        original_chars = len(text)
        heavy = path_is_heavy(path)
        remaining = max(max_total_chars - used, 0)
        allowed = min(max_file_chars, remaining)
        if heavy or allowed <= 0:
            snippet = ""
            retained = 0
            truncated = original_chars > 0
        else:
            snippet = text[:allowed]
            retained = len(snippet)
            truncated = original_chars > retained
            used += retained
        snippets.append(
            {
                "path": path,
                "status": status_by_path.get(path, ""),
                "heavy_path": heavy,
                "truncated": truncated,
                "original_chars": original_chars,
                "retained_chars": retained,
                "snippet": snippet,
            }
        )
    return snippets


def collect_latest_commit(repo_path: str, warnings: list[str]) -> dict[str, str]:
    result = run_git(repo_path, ["log", "-1", "--pretty=format:%H%n%s%n%b"], check=False)
    if result.returncode != 0:
        warnings.append("无法读取最新提交信息，仓库可能还没有提交历史。")
        return {"commit_hash": "", "subject": "", "body": ""}
    lines = result.stdout.splitlines()
    return {
        "commit_hash": lines[0].strip() if len(lines) >= 1 else "",
        "subject": lines[1].strip() if len(lines) >= 2 else "",
        "body": "\n".join(lines[2:]).strip() if len(lines) >= 3 else "",
    }


def resolve_git_scope(repo_path: str) -> tuple[str, str]:
    requested = Path(repo_path).expanduser()
    repo = str(requested)
    top_level = run_git(repo, ["rev-parse", "--show-toplevel"], check=False)
    if top_level.returncode != 0:
        raise ValueError(f"repo_path 不是有效 Git 仓库: {repo_path}")
    git_root = Path(top_level.stdout.strip() or repo).resolve()
    requested_abs = requested.resolve()
    try:
        relative_scope = requested_abs.relative_to(git_root).as_posix()
    except ValueError:
        relative_scope = ""
    if relative_scope == ".":
        relative_scope = ""
    return git_root.as_posix(), relative_scope


def git_args_with_scope(args: list[str], relative_scope: str) -> list[str]:
    if not relative_scope:
        return args
    return [*args, "--", relative_scope]


def normalize_status_lines(status_lines: list[str], relative_scope: str) -> list[str]:
    if not relative_scope:
        return status_lines
    prefix = f"{relative_scope.rstrip('/')}/"
    scoped: list[str] = []
    for line in status_lines:
        if len(line) < 4:
            continue
        status = line[:3]
        path = line[3:]
        if path == relative_scope or path.startswith(prefix):
            scoped.append(f"{status}{path}")
    return scoped


def collect_git_snapshot(repo_path: str = ".") -> dict[str, Any]:
    warnings: list[str] = []
    normalized_repo, relative_scope = resolve_git_scope(repo_path)

    status_lines = split_lines(run_git(normalized_repo, ["status", "--short"]).stdout)
    status_lines = normalize_status_lines(status_lines, relative_scope)
    diff_names = split_lines(
        run_git(normalized_repo, git_args_with_scope(["diff", "HEAD", "--name-only"], relative_scope), check=False).stdout
    )
    diff_result = run_git(normalized_repo, git_args_with_scope(["diff", "HEAD"], relative_scope), check=False)
    diff_text = diff_result.stdout if diff_result.returncode == 0 else ""
    if diff_result.returncode != 0:
        warnings.append("无法读取 git diff HEAD，仓库可能还没有提交历史。")
    diff_stat_result = run_git(normalized_repo, git_args_with_scope(["diff", "HEAD", "--stat"], relative_scope), check=False)
    diff_stat = diff_stat_result.stdout if diff_stat_result.returncode == 0 else ""
    latest_commit = collect_latest_commit(normalized_repo, warnings)
    if not status_lines and not diff_names and not diff_text:
        warnings.append("当前工作区没有检测到未提交变更。")

    return build_snapshot(
        repo_path=normalized_repo,
        requested_repo_path=str(Path(repo_path).expanduser()),
        relative_scope=relative_scope,
        diff_text=diff_text,
        diff_stat=diff_stat,
        diff_names=diff_names,
        status_lines=status_lines,
        latest_commit_context=latest_commit,
        warnings=warnings,
    )


def build_snapshot(
    repo_path: str = ".",
    requested_repo_path: str = "",
    relative_scope: str = "",
    diff_text: str = "",
    diff_stat: str = "",
    diff_names: list[str] | None = None,
    status_lines: list[str] | None = None,
    latest_commit_context: dict[str, str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    diff_names = diff_names or []
    status_lines = status_lines or []
    warnings = warnings or []
    changed_files_index = build_changed_files_index(diff_names=diff_names, status_lines=status_lines)
    return {
        "git_diff_snapshot": {
            "diff_text": diff_text,
            "diff_stat": diff_stat,
            "diff_name_only": diff_names,
            "status_lines": status_lines,
        },
        "latest_commit_context": latest_commit_context or {
            "commit_hash": "",
            "subject": "",
            "body": "",
        },
        "changed_files_index": changed_files_index,
        "git_collection_log": {
            "repo_path": repo_path,
            "requested_repo_path": requested_repo_path or repo_path,
            "relative_scope": relative_scope,
            "status": "ok",
            "warnings": warnings,
        },
    }


def build_compact_context(
    snapshot: dict[str, Any],
    *,
    max_total_chars: int = DEFAULT_TOTAL_DIFF_BUDGET,
    max_file_chars: int = DEFAULT_FILE_DIFF_BUDGET,
) -> dict[str, Any]:
    git_diff = snapshot.get("git_diff_snapshot", {})
    if not isinstance(git_diff, dict):
        git_diff = {}
    diff_text = str(git_diff.get("diff_text", ""))
    diff_names = [str(item) for item in git_diff.get("diff_name_only", []) if str(item).strip()]
    status_lines = [str(item) for item in git_diff.get("status_lines", []) if str(item).strip()]
    changed_files_index = snapshot.get("changed_files_index", {})
    if not isinstance(changed_files_index, dict):
        changed_files_index = build_changed_files_index(diff_names=diff_names, status_lines=status_lines)
    files = [str(item) for item in changed_files_index.get("files", []) if str(item).strip()]
    snippets = build_diff_snippets(
        diff_text,
        status_lines,
        max_total_chars=max_total_chars,
        max_file_chars=max_file_chars,
    )
    retained_chars = sum(int(item.get("retained_chars", 0)) for item in snippets)
    original_chars = sum(int(item.get("original_chars", 0)) for item in snippets)
    truncated_files = [item["path"] for item in snippets if item.get("truncated")]
    heavy_files = [path for path in files if path_is_heavy(path)]
    log = snapshot.get("git_collection_log", {})
    warnings = list(log.get("warnings", [])) if isinstance(log, dict) else []
    if truncated_files:
        warnings.append("diff 已按 compact 预算裁剪，完整内容保留在 .lgwf/git_context_snapshot.json。")
    if heavy_files:
        warnings.append("检测到重型路径或二进制候选，compact 上下文仅记录统计。")
    return {
        "git_diff_compact": {
            "diff_stat": str(git_diff.get("diff_stat", "")),
            "diff_name_only": diff_names,
            "status_lines": status_lines,
            "directory_groups": build_directory_groups(files),
            "diff_snippets": snippets,
        },
        "latest_commit_context": snapshot.get("latest_commit_context", {}),
        "changed_files_index": changed_files_index,
        "git_collection_log": {
            **(log if isinstance(log, dict) else {}),
            "warnings": warnings,
            "compact_source_file": ".lgwf/git_context_snapshot.json",
        },
        "context_budget": {
            "max_total_diff_chars": max_total_chars,
            "max_file_diff_chars": max_file_chars,
            "original_diff_chars": len(diff_text),
            "original_snippet_chars": original_chars,
            "retained_diff_chars": retained_chars,
            "truncated_files": truncated_files,
            "heavy_files": heavy_files,
        },
    }


def main() -> None:
    snapshot = collect_git_snapshot(repo_path=repo_path_from_scope())
    output_path = Path(".lgwf/git_context_snapshot.json")
    compact_path = Path(".lgwf/git_context_compact.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = build_compact_context(snapshot)
    compact_path.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.git_context_snapshot": snapshot,
        "git_diff_brief.git_context_compact": compact,
        "git_diff_brief.git_diff_snapshot": snapshot["git_diff_snapshot"],
        "git_diff_brief.latest_commit_context": snapshot["latest_commit_context"],
        "git_diff_brief.changed_files_index": snapshot["changed_files_index"],
        "git_diff_brief.git_collection_log": snapshot["git_collection_log"],
        "git_diff_brief.git_context_collection_result": {
            "ok": True,
            "output_file": ".lgwf/git_context_snapshot.json",
            "compact_output_file": ".lgwf/git_context_compact.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
