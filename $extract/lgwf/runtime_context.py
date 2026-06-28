from contextlib import contextmanager
import contextvars
from pathlib import Path
from typing import Iterator


_WORKSPACE_ROOT: contextvars.ContextVar[Path | None] = contextvars.ContextVar("lgwf_workspace_root", default=None)
_WORKFLOW_ROOT: contextvars.ContextVar[Path | None] = contextvars.ContextVar("lgwf_workflow_root", default=None)
_WORK_DIR_ROOT: contextvars.ContextVar[Path | None] = contextvars.ContextVar("lgwf_work_dir_root", default=None)


@contextmanager
def use_workspace_root(workspace_root: Path | None) -> Iterator[None]:
    token = _WORKSPACE_ROOT.set(workspace_root.resolve() if workspace_root is not None else None)
    try:
        yield
    finally:
        _WORKSPACE_ROOT.reset(token)


def get_workspace_root() -> Path | None:
    return _WORKSPACE_ROOT.get()


@contextmanager
def use_work_dir_root(work_dir_root: Path | None) -> Iterator[None]:
    token = _WORK_DIR_ROOT.set(work_dir_root.resolve() if work_dir_root is not None else None)
    try:
        yield
    finally:
        _WORK_DIR_ROOT.reset(token)


def get_work_dir_root() -> Path | None:
    return _WORK_DIR_ROOT.get()


@contextmanager
def use_workflow_root(workflow_root: Path | None) -> Iterator[None]:
    token = _WORKFLOW_ROOT.set(workflow_root.resolve() if workflow_root is not None else None)
    try:
        yield
    finally:
        _WORKFLOW_ROOT.reset(token)


def get_workflow_root() -> Path | None:
    return _WORKFLOW_ROOT.get()
