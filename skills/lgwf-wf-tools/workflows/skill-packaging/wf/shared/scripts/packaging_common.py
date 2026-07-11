"""skill-packaging 共享 helper。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGER_NAME = "lgwf-wf-tools/skill-packaging"
DEFAULT_EXCLUDED_NAMES = {
    ".git",
    ".lgwf",
    ".local",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "reports",
    "ws",
}
DEFAULT_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def find_workspace_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "skills").is_dir():
            return candidate
    raise RuntimeError(f"无法从 {start} 推导 workspace root")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_stdin_object() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if raw:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("stdin payload 必须是 JSON object")
        return payload
    fallback = Path.cwd() / ".lgwf" / "input_state.json"
    if fallback.is_file():
        payload = json.loads(fallback.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload
    return {}


def bool_value(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def resolve_user_path(work_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path.strip())
    if candidate.is_absolute():
        return candidate.resolve()
    return (find_workspace_root(work_dir) / candidate).resolve()


def default_runtime_source(work_dir: Path) -> Path:
    workspace_root = find_workspace_root(work_dir)
    return (
        workspace_root
        / "skills"
        / "lgwf-wf-tools"
        / "vendor"
        / "lgwf-client-assist"
    ).resolve()


def output_skill_path(source_skill: Path, output_parent: Path) -> Path:
    return output_parent.resolve() / source_skill.resolve().name


def validate_source_skill(source_skill: Path) -> list[str]:
    required = [
        source_skill / "SKILL.md",
        source_skill / "AGENTS.md",
        source_skill / "README.md",
        source_skill / "wf" / "workflow.lgwf",
    ]
    issues: list[str] = []
    for path in required:
        if not path.is_file():
            issues.append(f"缺少必需文件: {path.relative_to(source_skill).as_posix()}")
    return issues


def validate_runtime(runtime_source: Path) -> list[str]:
    required = [
        runtime_source / "AGENTS.md",
        runtime_source / "scripts" / "lgwf.py",
    ]
    issues: list[str] = []
    for path in required:
        if not path.is_file():
            issues.append(f"runtime 缺少必需文件: {path.relative_to(runtime_source).as_posix()}")
    return issues


def _ignore_names(_dir: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        if name in DEFAULT_EXCLUDED_NAMES or Path(name).suffix in DEFAULT_EXCLUDED_SUFFIXES:
            ignored.add(name)
    return ignored


def remove_existing_output(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def copy_tree_filtered(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=_ignore_names)


def write_local_runner(output_skill: Path) -> Path:
    scripts_dir = output_skill / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    runner = scripts_dir / "run_local_lgwf_workflow.py"
    runner.write_text(
        '''from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
LGWF_PY = SKILL_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command = [
        sys.executable,
        str(LGWF_PY),
        "run",
        "--workflow-lgwf",
        "wf/workflow.lgwf",
        "--work-dir",
        "ws",
        *args,
    ]
    completed = subprocess.run(command, cwd=str(SKILL_ROOT))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
''',
        encoding="utf-8",
    )
    return runner


def write_packaging_manifest(source_skill: Path, output_skill: Path, runtime_source: Path) -> Path:
    manifest = {
        "packager": PACKAGER_NAME,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_skill_name": source_skill.name,
        "source_skill_path": str(source_skill.resolve()),
        "runtime_source_path": str(runtime_source.resolve()),
        "runtime_relative_path": "vendor/lgwf-client-assist",
        "local_runner": "scripts/run_local_lgwf_workflow.py",
        "excluded_names": sorted(DEFAULT_EXCLUDED_NAMES),
        "excluded_suffixes": sorted(DEFAULT_EXCLUDED_SUFFIXES),
    }
    manifest_path = output_skill / "PACKAGING_MANIFEST.json"
    write_json(manifest_path, manifest)
    return manifest_path


def load_lgwf_artifact(work_dir: Path, file_name: str) -> dict[str, Any]:
    return read_json(work_dir / ".lgwf" / file_name)


def write_lgwf_artifact(work_dir: Path, file_name: str, payload: Any) -> Path:
    path = work_dir / ".lgwf" / file_name
    write_json(path, payload)
    return path


def summarize_tree(path: Path) -> dict[str, Any]:
    files = [item for item in path.rglob("*") if item.is_file()] if path.exists() else []
    return {
        "exists": path.exists(),
        "path": str(path),
        "file_count": len(files),
    }


def run_audit(lgwf_py: Path, workflow_lgwf: Path, cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(lgwf_py), "audit", str(workflow_lgwf)],
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
