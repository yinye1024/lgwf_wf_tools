import os
import pathlib
import shutil
import stat
import fnmatch
import hashlib
from datetime import datetime, timezone
from typing import Any


def ensure_dir(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    raw_paths = options.get("path")
    if isinstance(raw_paths, str):
        paths = [raw_paths]
    elif isinstance(raw_paths, list) and all(isinstance(item, str) for item in raw_paths):
        paths = raw_paths
    else:
        raise ValueError("options.path must be a string or list of strings.")

    created: list[str] = []
    for raw_path in paths:
        path = resolve_workspace_path(workspace_root, raw_path, "options.path")
        path.mkdir(parents=True, exist_ok=True)
        created.append(str(path))
    return {"created": created}


def write_text_file(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    path = resolve_workspace_path(workspace_root, options.get("path"), "options.path")
    content = options.get("content", "")
    append = options.get("append", False)
    if not isinstance(content, str):
        raise ValueError("options.content must be a string.")
    if not isinstance(append, bool):
        raise ValueError("options.append must be a boolean.")

    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8", newline="") as handle:
        handle.write(content)
    return {"path": str(path), "append": append}


def file_replace(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    source_dir = resolve_workspace_path(workspace_root, options.get("source_dir"), "options.source_dir")
    output_dir = resolve_workspace_path(workspace_root, options.get("output_dir"), "options.output_dir")
    exec_log_dir = resolve_workspace_path(workspace_root, options.get("exec_log_dir"), "options.exec_log_dir")
    token_map = options.get("token_map", {})
    dry_run = options.get("dry_run", False)
    clear_output_dir = options.get("clear_output_dir", False)

    if not source_dir.is_dir():
        raise ValueError(f"options.source_dir does not exist or is not a directory: {source_dir}")
    if not isinstance(token_map, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in token_map.items()
    ):
        raise ValueError("options.token_map must be an object with string keys and string values.")
    if not isinstance(dry_run, bool):
        raise ValueError("options.dry_run must be a boolean.")
    if not isinstance(clear_output_dir, bool):
        raise ValueError("options.clear_output_dir must be a boolean.")

    source_files = _preflight_file_replace(source_dir)
    operations: list[dict[str, object]] = []
    if clear_output_dir and output_dir.exists() and not dry_run:
        shutil.rmtree(output_dir)
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    for source_path in source_files:
        relative_path = source_path.relative_to(source_dir)
        target_path = output_dir / relative_path
        data = source_path.read_bytes()
        binary = looks_binary(data)
        replaced = False

        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)

        if binary:
            if not dry_run:
                target_path.write_bytes(data)
        else:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                binary = True
                if not dry_run:
                    target_path.write_bytes(data)
                operations.append(
                    {
                        "source": str(source_path),
                        "target": str(target_path),
                        "binary": binary,
                        "replaced": replaced,
                    }
                )
                continue
            next_text = text
            for token, replacement in token_map.items():
                next_text = next_text.replace(token, replacement)
            replaced = next_text != text
            if not dry_run:
                target_path.write_text(next_text, encoding="utf-8")

        operations.append(
            {
                "source": str(source_path),
                "target": str(target_path),
                "binary": binary,
                "replaced": replaced,
            }
        )

    exec_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = exec_log_dir / "FILE_REPLACE_EXEC.md"
    lines = [
        "# FILE_REPLACE_EXEC",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- source_dir: {source_dir}",
        f"- output_dir: {output_dir}",
        f"- dry_run: {dry_run}",
        f"- clear_output_dir: {clear_output_dir}",
        "",
        "## Files",
        "",
    ]
    for operation in operations:
        lines.append(
            f"- `{operation['source']}` -> `{operation['target']}` "
            f"(binary={operation['binary']}, replaced={operation['replaced']})"
        )
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"files": len(operations), "log": str(log_path), "dry_run": dry_run}


def copy_file(
    options: dict[str, Any],
    *,
    workspace_root: pathlib.Path | None = None,
    cwd: pathlib.Path | None = None,
) -> dict[str, Any]:
    source, destination, overwrite = _copy_paths(options, workspace_root=workspace_root, cwd=cwd)
    if not source.is_file():
        raise ValueError(f"options.source does not exist or is not a file: {source}")
    _reject_link_or_reparse(source, "options.source")
    _reject_existing_link_components(destination, "options.destination")
    if source == destination:
        raise ValueError("options.source and options.destination must be different.")
    if destination.exists() and not overwrite:
        raise ValueError(f"destination already exists: {destination}")
    if destination.exists() and not destination.is_file():
        raise ValueError(f"destination exists and is not a file: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {"source": str(source), "destination": str(destination), "overwrite": overwrite}


def copy_directory(
    options: dict[str, Any],
    *,
    workspace_root: pathlib.Path | None = None,
    cwd: pathlib.Path | None = None,
) -> dict[str, Any]:
    source, destination, overwrite = _copy_paths(options, workspace_root=workspace_root, cwd=cwd)
    if not source.is_dir():
        raise ValueError(f"options.source does not exist or is not a directory: {source}")
    _reject_link_or_reparse(source, "options.source")
    _reject_existing_link_components(destination, "options.destination")
    if _is_relative_to(source, destination) or _is_relative_to(destination, source):
        raise ValueError("options.source and options.destination must not contain each other.")
    if destination.exists() and not overwrite:
        raise ValueError(f"destination already exists: {destination}")
    if destination.exists() and not destination.is_dir():
        raise ValueError(f"destination exists and is not a directory: {destination}")

    entries = _preflight_directory_copy(source, destination, overwrite)
    destination.mkdir(parents=True, exist_ok=True)
    directories: list[tuple[pathlib.Path, pathlib.Path]] = []
    for source_path, destination_path, is_directory in entries:
        if is_directory:
            destination_path.mkdir(parents=True, exist_ok=True)
            directories.append((source_path, destination_path))
        else:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
    for source_path, destination_path in reversed(directories):
        shutil.copystat(source_path, destination_path, follow_symlinks=False)
    shutil.copystat(source, destination, follow_symlinks=False)
    return {
        "source": str(source),
        "destination": str(destination),
        "overwrite": overwrite,
        "files": sum(1 for _source, _destination, is_directory in entries if not is_directory),
    }


def sandbox_prepare(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    spec = _sandbox_spec(options, workspace_root)
    sandbox_root = spec["sandbox_root"]
    if sandbox_root.exists():
        _reject_link_or_reparse(sandbox_root, "options.sandbox_path")
        shutil.rmtree(sandbox_root)

    copied: dict[str, int] = {}
    for root_name, root_spec in spec["roots"].items():
        baseline_root = sandbox_root / "baseline" / root_name
        candidate_root = sandbox_root / "candidate" / root_name
        baseline_count = _copy_filtered_tree(
            root_spec["source_root"],
            baseline_root,
            root_spec["include"],
            root_spec["exclude"],
        )
        candidate_count = _copy_filtered_tree(
            root_spec["source_root"],
            candidate_root,
            root_spec["include"],
            root_spec["exclude"],
        )
        copied[root_name] = min(baseline_count, candidate_count)

    result = {
        "sandbox_root": str(sandbox_root),
        "baseline_root": str(sandbox_root / "baseline"),
        "candidate_root": str(sandbox_root / "candidate"),
        "copied": copied,
    }
    _write_json(sandbox_root / "prepare.json", result)
    return result


def sandbox_diff(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    spec = _sandbox_spec(options, workspace_root)
    sandbox_root = spec["sandbox_root"]
    changes: list[dict[str, Any]] = []
    for root_name, root_spec in spec["roots"].items():
        baseline_root = sandbox_root / "baseline" / root_name
        candidate_root = sandbox_root / "candidate" / root_name
        paths = sorted(
            set(_file_fingerprints(baseline_root, root_spec["include"], root_spec["exclude"]))
            | set(_file_fingerprints(candidate_root, root_spec["include"], root_spec["exclude"]))
        )
        baseline = _file_fingerprints(baseline_root, root_spec["include"], root_spec["exclude"])
        candidate = _file_fingerprints(candidate_root, root_spec["include"], root_spec["exclude"])
        for rel_path in paths:
            before = baseline.get(rel_path)
            after = candidate.get(rel_path)
            if before == after:
                continue
            if before is None:
                status = "added"
            elif after is None:
                status = "deleted"
            else:
                status = "modified"
            changes.append({"root": root_name, "path": rel_path, "status": status})

    result = {"sandbox_root": str(sandbox_root), "changes": changes}
    _write_json(sandbox_root / "diff.json", result)
    return result


def sandbox_promote(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    spec = _sandbox_spec(options, workspace_root)
    sandbox_root = spec["sandbox_root"]
    promoted: list[dict[str, str]] = []
    deleted: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []

    for root_name, root_spec in spec["roots"].items():
        conflicts.extend(_sandbox_promote_conflicts(sandbox_root, root_name, root_spec))
    if conflicts:
        conflict_paths = ", ".join(f"{item['root']}:{item['path']}" for item in conflicts[:5])
        if len(conflicts) > 5:
            conflict_paths = f"{conflict_paths}, ..."
        raise ValueError(f"Sandbox promote conflict: real root changed since baseline: {conflict_paths}")

    for root_name, root_spec in spec["roots"].items():
        baseline_root = sandbox_root / "baseline" / root_name
        candidate_root = sandbox_root / "candidate" / root_name
        destination_root = root_spec["source_root"]
        baseline = _file_fingerprints(
            baseline_root,
            root_spec["promote_include"],
            root_spec["exclude"],
        )
        candidate = _file_fingerprints(
            candidate_root,
            root_spec["promote_include"],
            root_spec["exclude"],
        )
        for source_path in _iter_filtered_files(
            candidate_root,
            root_spec["promote_include"],
            root_spec["exclude"],
        ):
            rel_path = source_path.relative_to(candidate_root).as_posix()
            destination = destination_root / rel_path
            _reject_existing_link_components(destination, "promote destination")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            promoted.append(
                {
                    "root": root_name,
                    "path": rel_path,
                    "destination": str(destination),
                }
            )
        for rel_path in sorted(set(baseline) - set(candidate)):
            destination = destination_root / rel_path
            _reject_existing_link_components(destination, "promote delete destination")
            if destination.exists():
                destination.unlink()
                _remove_empty_parents(destination.parent, destination_root)
                deleted.append(
                    {
                        "root": root_name,
                        "path": rel_path,
                        "destination": str(destination),
                    }
                )

    result = {
        "sandbox_root": str(sandbox_root),
        "promoted": len(promoted),
        "deleted": len(deleted),
        "files": promoted,
        "deleted_files": deleted,
    }
    _write_json(sandbox_root / "promote.json", result)
    return result


def sandbox_archive(options: dict[str, Any], *, workspace_root: pathlib.Path) -> dict[str, Any]:
    spec = _sandbox_spec(options, workspace_root)
    sandbox_root = spec["sandbox_root"]
    validation = options.get("validation", {})
    decision = options.get("decision", {})
    if not isinstance(validation, dict):
        raise ValueError("options.validation must be an object when provided.")
    if not isinstance(decision, dict):
        raise ValueError("options.decision must be an object when provided.")
    _write_json(sandbox_root / "validation.json", validation)
    _write_json(sandbox_root / "decision.json", decision)
    return {
        "sandbox_root": str(sandbox_root),
        "validation_path": str(sandbox_root / "validation.json"),
        "decision_path": str(sandbox_root / "decision.json"),
    }


def resolve_workspace_path(root: pathlib.Path, raw_path: object, label: str) -> pathlib.Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    path = pathlib.Path(raw_path)
    if path.is_absolute():
        raise ValueError(f"{label} must be relative.")
    if ".." in path.parts:
        raise ValueError(f"{label} must not contain '..'.")
    resolved_root = root.resolve()
    candidate = pathlib.Path(os.path.abspath(resolved_root / path))
    _reject_existing_link_components(candidate, label)
    resolved = candidate.resolve()
    if not _is_relative_to(resolved, resolved_root):
        raise ValueError(f"{label} must stay inside workspace root.")
    return resolved


def _sandbox_spec(options: dict[str, Any], workspace_root: pathlib.Path) -> dict[str, Any]:
    if not isinstance(options, dict):
        raise ValueError("options must be an object.")
    sandbox_root = resolve_workspace_path(workspace_root, options.get("sandbox_path"), "options.sandbox_path")
    work_dir = _sandbox_root_spec(options.get("work_dir"), "options.work_dir")
    roots: dict[str, dict[str, Any]] = {
        "work_dir": {
            **work_dir,
            "source_root": _sandbox_source_root(options.get("_source_root"), workspace_root),
        }
    }

    target_dir = options.get("target_dir")
    if target_dir is not None:
        if not isinstance(target_dir, dict):
            raise ValueError("options.target_dir must be an object when provided.")
        target_path = _sandbox_source_root(
            target_dir.get("_source_root"),
            workspace_root,
            fallback_path=target_dir.get("path"),
            fallback_label="options.target_dir.path",
        )
        roots["target_dir"] = {
            **_sandbox_root_spec(target_dir, "options.target_dir"),
            "source_root": target_path,
        }

    for root_name, root_spec in roots.items():
        source_root = root_spec["source_root"]
        if not source_root.is_dir():
            raise ValueError(f"{root_name} source root does not exist or is not a directory: {source_root}")
        _reject_link_or_reparse(source_root, f"{root_name} source root")

    return {"sandbox_root": sandbox_root, "roots": roots}


def _sandbox_source_root(
    value: object,
    workspace_root: pathlib.Path,
    *,
    fallback_path: object | None = None,
    fallback_label: str | None = None,
) -> pathlib.Path:
    if isinstance(value, pathlib.Path):
        return value.resolve()
    if value is not None:
        raise ValueError("sandbox internal source root must be a pathlib.Path.")
    if fallback_path is not None and fallback_label is not None:
        return resolve_workspace_path(workspace_root, fallback_path, fallback_label)
    return workspace_root.resolve()


def _sandbox_root_spec(raw_spec: object, label: str) -> dict[str, list[str]]:
    if not isinstance(raw_spec, dict):
        raise ValueError(f"{label} must be an object.")
    include = _pattern_list(raw_spec.get("include"), f"{label}.include", required=True)
    exclude = _pattern_list(raw_spec.get("exclude", []), f"{label}.exclude", required=False)
    promote_include = _pattern_list(
        raw_spec.get("promote_include", include),
        f"{label}.promote_include",
        required=True,
    )
    return {
        "include": include,
        "exclude": _default_excludes() + exclude,
        "promote_include": promote_include,
    }


def _pattern_list(value: object, label: str, *, required: bool) -> list[str]:
    if (value is None or value == []) and not required:
        return []
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{label} must be a non-empty list of strings.")
    for pattern in value:
        path = pathlib.PurePosixPath(pattern.replace("\\", "/"))
        if path.is_absolute():
            raise ValueError(f"{label} patterns must be relative.")
        if ".." in path.parts:
            raise ValueError(f"{label} patterns must not contain '..'.")
    return [item.replace("\\", "/") for item in value]


def _default_excludes() -> list[str]:
    return [".lgwf/**", "__pycache__/**", "*.pyc", "*.log"]


def _copy_filtered_tree(
    source_root: pathlib.Path,
    destination_root: pathlib.Path,
    include: list[str],
    exclude: list[str],
) -> int:
    count = 0
    destination_root.mkdir(parents=True, exist_ok=True)
    for source_path in _iter_filtered_files(source_root, include, exclude):
        rel_path = source_path.relative_to(source_root)
        destination = destination_root / rel_path
        _reject_existing_link_components(destination, "sandbox destination")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        count += 1
    return count


def _iter_filtered_files(
    root: pathlib.Path,
    include: list[str],
    exclude: list[str],
) -> list[pathlib.Path]:
    if not root.exists():
        return []
    files: list[pathlib.Path] = []

    def visit(directory: pathlib.Path) -> None:
        with os.scandir(directory) as iterator:
            for entry in iterator:
                path = pathlib.Path(entry.path)
                rel_path = path.relative_to(root).as_posix()
                if _matches_any(rel_path, exclude):
                    continue
                _reject_link_or_reparse(path, "sandbox source entry")
                if entry.is_dir(follow_symlinks=False):
                    visit(path)
                elif entry.is_file(follow_symlinks=False) and _matches_any(rel_path, include):
                    files.append(path)

    visit(root)
    return sorted(files)


def _file_fingerprints(root: pathlib.Path, include: list[str], exclude: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in _iter_filtered_files(root, include, exclude):
        rel_path = path.relative_to(root).as_posix()
        result[rel_path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _sandbox_promote_conflicts(
    sandbox_root: pathlib.Path,
    root_name: str,
    root_spec: dict[str, Any],
) -> list[dict[str, str]]:
    baseline_root = sandbox_root / "baseline" / root_name
    candidate_root = sandbox_root / "candidate" / root_name
    destination_root = root_spec["source_root"]
    baseline = _file_fingerprints(
        baseline_root,
        root_spec["promote_include"],
        root_spec["exclude"],
    )
    candidate = _file_fingerprints(
        candidate_root,
        root_spec["promote_include"],
        root_spec["exclude"],
    )
    destination = _file_fingerprints(
        destination_root,
        root_spec["promote_include"],
        root_spec["exclude"],
    )
    conflicts = []
    for rel_path in sorted(set(baseline) | set(candidate)):
        if destination.get(rel_path) != baseline.get(rel_path):
            conflicts.append(
                {
                    "root": root_name,
                    "path": rel_path,
                    "status": "changed_since_baseline",
                }
            )
    return conflicts


def _remove_empty_parents(path: pathlib.Path, stop_root: pathlib.Path) -> None:
    stop = stop_root.resolve()
    current = path
    while current.resolve() != stop and _is_relative_to(current.resolve(), stop):
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def _matches_any(path: str, patterns: list[str]) -> bool:
    parts = path.split("/")
    if ".lgwf" in parts and any(pattern == ".lgwf/**" for pattern in patterns):
        return True
    if "__pycache__" in parts and any(pattern == "__pycache__/**" for pattern in patterns):
        return True
    return any(pattern == "**" or fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(data), encoding="utf-8")


def json_dumps(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def looks_binary(data: bytes) -> bool:
    return b"\x00" in data


def is_link_or_reparse_point(path: pathlib.Path) -> bool:
    if path.is_symlink():
        return True
    file_attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(file_attributes & reparse_flag)


def _copy_paths(
    options: dict[str, Any],
    *,
    workspace_root: pathlib.Path | None,
    cwd: pathlib.Path | None,
) -> tuple[pathlib.Path, pathlib.Path, bool]:
    overwrite = options.get("overwrite", False)
    if not isinstance(overwrite, bool):
        raise ValueError("options.overwrite must be a boolean.")
    if workspace_root is not None:
        source = resolve_workspace_path(workspace_root, options.get("source"), "options.source")
        destination = resolve_workspace_path(
            workspace_root,
            options.get("destination"),
            "options.destination",
        )
        return source, destination, overwrite
    base = (cwd or pathlib.Path.cwd()).resolve()
    source = _resolve_external_path(options.get("source"), base, "options.source")
    destination = _resolve_external_path(options.get("destination"), base, "options.destination")
    return source, destination, overwrite


def _resolve_external_path(raw_path: object, cwd: pathlib.Path, label: str) -> pathlib.Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    path = pathlib.Path(raw_path).expanduser()
    if not path.is_absolute():
        path = cwd / path
    return pathlib.Path(os.path.abspath(path))


def _preflight_directory_copy(
    source_root: pathlib.Path,
    destination_root: pathlib.Path,
    overwrite: bool,
) -> list[tuple[pathlib.Path, pathlib.Path, bool]]:
    entries: list[tuple[pathlib.Path, pathlib.Path, bool]] = []

    def visit(directory: pathlib.Path) -> None:
        with os.scandir(directory) as iterator:
            for entry in iterator:
                source = pathlib.Path(entry.path)
                _reject_link_or_reparse(source, "source entry")
                destination = destination_root / source.relative_to(source_root)
                is_directory = entry.is_dir(follow_symlinks=False)
                if destination.exists():
                    _reject_link_or_reparse(destination, "destination entry")
                    if is_directory and not destination.is_dir():
                        raise ValueError(f"destination conflicts with source directory: {destination}")
                    if not is_directory and not destination.is_file():
                        raise ValueError(f"destination conflicts with source file: {destination}")
                    if not is_directory and not overwrite:
                        raise ValueError(f"destination already exists: {destination}")
                entries.append((source, destination, is_directory))
                if is_directory:
                    visit(source)

    visit(source_root)
    return entries


def _preflight_file_replace(source_root: pathlib.Path) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []

    def visit(directory: pathlib.Path) -> None:
        with os.scandir(directory) as iterator:
            for entry in iterator:
                source = pathlib.Path(entry.path)
                _reject_link_or_reparse(source, "source entry")
                if entry.is_dir(follow_symlinks=False):
                    visit(source)
                elif entry.is_file(follow_symlinks=False):
                    files.append(source)

    visit(source_root)
    return sorted(files)


def _reject_link_or_reparse(path: pathlib.Path, label: str) -> None:
    if is_link_or_reparse_point(path):
        raise ValueError(f"{label} is a symbolic link or reparse point: {path}")


def _reject_existing_link_components(path: pathlib.Path, label: str) -> None:
    current = path
    existing: list[pathlib.Path] = []
    while True:
        if current.exists() or current.is_symlink():
            existing.append(current)
        if current.parent == current:
            break
        current = current.parent
    for candidate in reversed(existing):
        _reject_link_or_reparse(candidate, label)


def _is_relative_to(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
