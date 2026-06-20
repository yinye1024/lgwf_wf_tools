from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, write_json


EXCLUDED_DIRS = {".git", ".hg", ".svn", ".lgwf", "__pycache__", ".pytest_cache"}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_snapshot(package_root: Path) -> dict[str, Any]:
    files: dict[str, str] = {}
    for path in package_root.rglob("*"):
        if not path.is_file() or _is_excluded(path.relative_to(package_root)):
            continue
        relative = path.relative_to(package_root).as_posix()
        files[relative] = _hash_file(path)
    return {"package_root": str(package_root), "files": files}


def main() -> None:
    target = load_self_fix_target()
    package_root = Path(str(target.get("target_package_root") or "")).resolve()
    snapshot = capture_snapshot(package_root)
    write_json(lgwf_dir() / "target_repair_snapshot.json", snapshot)
    append_history({"event": "repair_snapshot_captured", "file_count": len(snapshot["files"])})
    output_state({"target_repair_snapshot": snapshot})


if __name__ == "__main__":
    main()
