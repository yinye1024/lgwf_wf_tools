from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any


RUNNER_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = RUNNER_ROOT.parent
DEFAULT_FACADE_ROOT = SKILLS_ROOT / "lgwf-wf-tools"


def emit_json(data: dict[str, Any], *, exit_code: int = 0) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(payload.encode("utf-8"))
    raise SystemExit(exit_code)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_facade_root(raw: str | None) -> Path:
    root = Path(raw).resolve() if raw else DEFAULT_FACADE_ROOT.resolve()
    if not (root / "registry.json").is_file():
        raise FileNotFoundError(f"registry.json not found under facade root: {root}")
    if not (root / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py").is_file():
        raise FileNotFoundError(f"lgwf.py not found under facade root: {root}")
    return root


def load_registry(facade_root: Path) -> dict[str, Any]:
    data = read_json(facade_root / "registry.json")
    if not isinstance(data, dict) or not isinstance(data.get("workflows"), list):
        raise ValueError("registry.json must contain workflows list")
    return data


def find_workflow(registry: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    for item in registry.get("workflows", []):
        if isinstance(item, dict) and item.get("id") == workflow_id:
            return item
    raise KeyError(f"workflow id not found in registry: {workflow_id}")


def safe_relative_path(raw: Any, *, field: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} must be a non-empty relative path")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be safe relative path: {raw}")
    return path


def slugify(raw: str | None, fallback: str) -> str:
    source = raw or fallback
    source = source.strip().lower()
    source = re.sub(r"[^a-z0-9._-]+", "-", source)
    source = re.sub(r"-{2,}", "-", source).strip("-._")
    return source[:48] or fallback


def make_facade_session_id(target_slug: str | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = slugify(target_slug, "run")
    return f"{now}-{slug}-{secrets.token_hex(4)}"


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def resolve_work_dir(
    *,
    facade_root: Path,
    runner_root: Path,
    workflow_id: str,
    target_slug: str | None,
    facade_session_id: str | None,
    create: bool,
) -> dict[str, Any]:
    facade_root = facade_root.resolve()
    runner_root = runner_root.resolve()
    registry = load_registry(facade_root)
    workflow = find_workflow(registry, workflow_id)
    workflow_lgwf = safe_relative_path(workflow.get("workflow_lgwf"), field="workflow_lgwf")
    registry_work_dir = safe_relative_path(workflow.get("work_dir"), field="work_dir")
    agents_md = safe_relative_path(workflow.get("agents_md"), field="agents_md")

    session_id = facade_session_id or make_facade_session_id(target_slug or workflow_id)
    session_slug = slugify(session_id, f"run-{short_hash(session_id)}")
    base_work_dir = (runner_root / "ws").resolve()
    resolved_work_dir = (base_work_dir / "sessions" / workflow_id / session_slug).resolve()

    try:
        resolved_work_dir.relative_to(base_work_dir.resolve())
    except ValueError as exc:
        raise ValueError("resolved work dir escaped base work dir") from exc

    if create:
        resolved_work_dir.mkdir(parents=True, exist_ok=False)

    return {
        "workflow_id": workflow_id,
        "facade_session_id": session_slug,
        "target_slug": target_slug or "",
        "facade_root": str(facade_root),
        "runner_root": str(runner_root),
        "workflow_lgwf": str((facade_root / workflow_lgwf).resolve()),
        "agents_md": str((facade_root / agents_md).resolve()),
        "registry_work_dir": str((facade_root / registry_work_dir).resolve()),
        "base_work_dir": str(base_work_dir),
        "resolved_work_dir": str(resolved_work_dir),
        "relative_resolved_work_dir": str(resolved_work_dir.relative_to(runner_root)),
    }


def lgwf_py(facade_root: Path) -> Path:
    return facade_root / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def run_command(args: list[str], *, cwd: Path, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def parse_json_stdout(proc: subprocess.CompletedProcess[str]) -> Any:
    stdout = proc.stdout.strip()
    if not stdout:
        raise ValueError("command produced empty stdout")
    return json.loads(stdout)


def add_common_facade_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--facade-root", help="lgwf-wf-tools 根目录；默认使用同级 skill")


def resolve_runner_root(raw: str | None) -> Path:
    return Path(raw).resolve() if raw else RUNNER_ROOT.resolve()


def add_common_runner_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runner-root", help="lgwf-wf-runner 根目录；默认使用当前 skill")
