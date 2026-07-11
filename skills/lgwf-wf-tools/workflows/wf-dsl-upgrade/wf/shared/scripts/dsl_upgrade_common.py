from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
TOOL_ROOT = PACKAGE_ROOT.parent.parent


def find_lgwf_py() -> Path:
    candidate_roots: list[Path] = []
    for env_name in ("LGWF_WF_TOOLS_ROOT", "LGWF_TOOL_ROOT"):
        raw_value = os.environ.get(env_name)
        if raw_value:
            candidate_roots.append(Path(raw_value).expanduser())
    for seed in (Path(__file__).resolve(), Path.cwd().resolve()):
        candidate_roots.extend(seed.parents)
    candidate_roots.append(TOOL_ROOT)

    seen: set[Path] = set()
    for root in candidate_roots:
        for base in (root, root / "skills" / "lgwf-wf-tools"):
            resolved = base.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidate = resolved / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
            if candidate.exists():
                return candidate
    return TOOL_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


LGWF_PY = find_lgwf_py()


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> Path:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def ensure_runtime_dirs(root: Path) -> tuple[Path, Path]:
    lgwf_dir = root / ".lgwf"
    reports_dir = root / "reports" / "wf-dsl-upgrade"
    lgwf_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    return lgwf_dir, reports_dir


def resolve_existing_path(raw_path: str) -> Path:
    return Path(raw_path).expanduser().resolve()


def path_is_authorized(target_path: Path, allowed_dirs: Iterable[Path]) -> bool:
    candidate = target_path.resolve()
    for raw_dir in allowed_dirs:
        allowed_dir = raw_dir.resolve()
        try:
            candidate.relative_to(allowed_dir)
        except ValueError:
            continue
        return True
    return False


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_text(text: str, limit: int = 1200) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def build_audit_command(target_path: Path, lgwf_py_path: Path | None = None) -> list[str]:
    script = Path(lgwf_py_path or LGWF_PY)
    return [sys.executable, script.as_posix(), "audit", Path(target_path).as_posix()]


def parse_audit_output(stdout: str) -> dict[str, Any] | None:
    cleaned = stdout.strip()
    if not cleaned:
        return None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def run_lgwf_audit(target_path: Path, lgwf_py_path: Path | None = None) -> dict[str, Any]:
    command = build_audit_command(target_path, lgwf_py_path)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    parsed = parse_audit_output(completed.stdout)
    diagnostics = parsed.get("diagnostics", []) if isinstance(parsed, dict) else []
    return {
        "target_path": str(target_path),
        "command": command,
        "returncode": completed.returncode,
        "passed": bool(parsed.get("passed", completed.returncode == 0)) if isinstance(parsed, dict) else completed.returncode == 0,
        "diagnostics": diagnostics if isinstance(diagnostics, list) else [],
        "audit_json": parsed,
        "stdout_excerpt": summarize_text(completed.stdout),
        "stderr_excerpt": summarize_text(completed.stderr),
    }


def diagnostic_identity(finding: dict[str, Any]) -> str:
    code = str(finding.get("code", "UNKNOWN")).strip()
    location = finding.get("location", {})
    if not isinstance(location, dict):
        location = {}
    path = str(location.get("path", "")).strip()
    line = str(location.get("line", "")).strip()
    column = str(location.get("column", "")).strip()
    message = str(finding.get("message", "")).strip()
    return "|".join([code, path, line, column, message])


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
