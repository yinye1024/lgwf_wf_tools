from __future__ import annotations

from pathlib import Path


def find_facade_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "registry.json").is_file() and (candidate / "SKILL.md").is_file():
            return candidate
    raise RuntimeError(f"cannot find lgwf-wf-tools facade root from {current}")


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = find_facade_root(SELF_IMPROVE_ROOT)
