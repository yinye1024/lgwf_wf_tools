from __future__ import annotations

import json
import subprocess
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


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
    latest_commit = collect_latest_commit(normalized_repo, warnings)
    if not status_lines and not diff_names and not diff_text:
        warnings.append("当前工作区没有检测到未提交变更。")

    return build_snapshot(
        repo_path=normalized_repo,
        requested_repo_path=str(Path(repo_path).expanduser()),
        relative_scope=relative_scope,
        diff_text=diff_text,
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


def main() -> None:
    snapshot = collect_git_snapshot(repo_path=repo_path_from_scope())
    output_path = Path(".lgwf/git_context_snapshot.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.git_context_snapshot": snapshot,
        "git_diff_brief.git_diff_snapshot": snapshot["git_diff_snapshot"],
        "git_diff_brief.latest_commit_context": snapshot["latest_commit_context"],
        "git_diff_brief.changed_files_index": snapshot["changed_files_index"],
        "git_diff_brief.git_collection_log": snapshot["git_collection_log"],
        "git_diff_brief.git_context_collection_result": {
            "ok": True,
            "output_file": ".lgwf/git_context_snapshot.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
