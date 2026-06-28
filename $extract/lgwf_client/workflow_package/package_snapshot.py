import os
import pathlib
import shutil
import stat
from typing import Any

import lgwf_tools.workspace_layout as workspace_layout_module


SNAPSHOT_DIR_NAME = "workflow"
WORKFLOW_SOURCE_FILENAME = "workflow.lgwf"
WORKFLOW_RUNTIME_FILENAME = "workflow.json"
EXCLUDED_DIRECTORY_NAMES = {".git", "__pycache__"}
COMPILED_FILE_PREFIX = ".lgwf-compiled-"


def copy_workflow_package(
    workflow_lgwf: str | pathlib.Path,
    work_dir: str | pathlib.Path,
) -> dict[str, Any]:
    source_path = pathlib.Path(workflow_lgwf).expanduser()
    if not source_path.is_file():
        raise ValueError(f"workflow-lgwf must be an existing file: {workflow_lgwf}")
    if source_path.name != WORKFLOW_SOURCE_FILENAME:
        raise ValueError(f"workflow-lgwf must be named {WORKFLOW_SOURCE_FILENAME}: {workflow_lgwf}")
    if is_link_or_reparse_point(source_path):
        raise ValueError(f"workflow package contains a symbolic link or reparse point: {source_path}")
    if is_link_or_reparse_point(source_path.parent):
        raise ValueError(f"workflow package root is a symbolic link or reparse point: {source_path.parent}")

    package_root = source_path.parent.resolve()
    work_root = pathlib.Path(work_dir).expanduser().resolve()
    if not work_root.is_dir():
        raise ValueError(f"work-dir must be an existing directory: {work_dir}")
    if package_root == work_root:
        raise ValueError("work-dir must not equal workflow package root")

    lgwf_root = workspace_layout_module.lgwf_dir(work_root)
    if lgwf_root.exists() and is_link_or_reparse_point(lgwf_root):
        raise ValueError(f"work-dir .lgwf is a symbolic link or reparse point: {lgwf_root}")
    snapshot_root = (lgwf_root / SNAPSHOT_DIR_NAME).resolve()
    if snapshot_root.exists():
        raise ValueError(f"workflow snapshot already exists; rerun cleanup is required: {snapshot_root}")

    excluded_work_root = work_root if _is_relative_to(work_root, package_root) else None
    entries = _preflight_entries(package_root, excluded_work_root)

    snapshot_root.mkdir(parents=True)
    try:
        _copy_entries(package_root, snapshot_root, entries)
    except Exception:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        raise

    return {
        "workflow_root": str(snapshot_root),
        "workflow_lgwf": str(snapshot_root / WORKFLOW_SOURCE_FILENAME),
        "workflow_json": str(snapshot_root / WORKFLOW_RUNTIME_FILENAME),
    }


def is_link_or_reparse_point(path: pathlib.Path) -> bool:
    if path.is_symlink():
        return True
    file_attributes = getattr(os.lstat(path), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(file_attributes & reparse_flag)


def _preflight_entries(
    package_root: pathlib.Path,
    excluded_work_root: pathlib.Path | None,
) -> list[tuple[pathlib.Path, bool]]:
    entries: list[tuple[pathlib.Path, bool]] = []

    def visit(directory: pathlib.Path) -> None:
        with os.scandir(directory) as iterator:
            for entry in iterator:
                source = pathlib.Path(entry.path)
                if _is_excluded(source, excluded_work_root):
                    continue
                if is_link_or_reparse_point(source):
                    relative = source.relative_to(package_root)
                    raise ValueError(
                        f"workflow package contains a symbolic link or reparse point: {relative}"
                    )
                is_directory = entry.is_dir(follow_symlinks=False)
                entries.append((source, is_directory))
                if is_directory:
                    visit(source)

    visit(package_root)
    return entries


def _copy_entries(
    package_root: pathlib.Path,
    snapshot_root: pathlib.Path,
    entries: list[tuple[pathlib.Path, bool]],
) -> None:
    directories: list[tuple[pathlib.Path, pathlib.Path]] = []
    for source, is_directory in entries:
        destination = snapshot_root / source.relative_to(package_root)
        if is_directory:
            destination.mkdir()
            directories.append((source, destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for source, destination in reversed(directories):
        shutil.copystat(source, destination, follow_symlinks=False)


def _is_excluded(source: pathlib.Path, excluded_work_root: pathlib.Path | None) -> bool:
    if source.name in EXCLUDED_DIRECTORY_NAMES:
        return True
    if source.name.startswith(COMPILED_FILE_PREFIX):
        return True
    if excluded_work_root is not None and source.resolve() == excluded_work_root:
        return True
    return False


def _is_relative_to(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
