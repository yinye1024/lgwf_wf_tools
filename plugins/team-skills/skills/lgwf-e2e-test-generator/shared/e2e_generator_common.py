from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


LGWF_DIR = Path(".lgwf")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"missing required JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def output_state(values: dict[str, Any]) -> None:
    print(json.dumps({f"lgwf_e2e.{key}": value for key, value in values.items()}, ensure_ascii=False))


def repo_rel_or_abs(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip()).strip("_").lower()
    return cleaned or "target_workflow"


def workflow_name_from_text(text: str) -> str | None:
    match = re.search(r"^\s*WORKFLOW\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", text, re.MULTILINE)
    return match.group(1) if match else None


def add_shared_to_path(script_file: str) -> None:
    current = Path(script_file).resolve()
    for parent in current.parents:
        shared = parent / "shared"
        if (shared / "e2e_generator_common.py").exists():
            sys.path.insert(0, str(shared))
            return
    raise RuntimeError("cannot locate shared/e2e_generator_common.py")
