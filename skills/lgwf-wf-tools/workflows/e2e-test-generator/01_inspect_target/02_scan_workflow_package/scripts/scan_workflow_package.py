from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, read_json, repo_rel_or_abs, write_json, output_state


SKIP_DIRS = {".git", ".lgwf", ".tmp", "__pycache__", "data", "reports", "ws", "node_modules"}


def should_skip(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in parts)


def collect_files(root: Path) -> dict[str, list[dict[str, str]]]:
    result = {"workflows": [], "prompts": [], "scripts": [], "approval_templates": []}
    for path in root.rglob("*"):
        if not path.is_file() or should_skip(path, root):
            continue
        relative = repo_rel_or_abs(path, root)
        item = {"path": relative}
        if path.name == "workflow.lgwf":
            result["workflows"].append(item)
        elif path.suffix.lower() == ".py" and "tests" not in path.parts:
            result["scripts"].append(item)
        elif path.suffix.lower() == ".md":
            text = path.read_text(encoding="utf-8", errors="replace")
            if "approval" in path.name.lower() or "confirm" in path.name.lower():
                result["approval_templates"].append(item)
            if "OUTPUT_JSON" in text or "Role" in text or "Task" in text:
                result["prompts"].append(item)
    return result


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    root = Path(request["workflow_root"])
    files = collect_files(root)
    inventory = {
        "workflow_root": root.as_posix(),
        "workflow_lgwf": request["workflow_lgwf"],
        "counts": {key: len(value) for key, value in files.items()},
        **files,
    }
    write_json(LGWF_DIR / "e2e_workflow_sources.json", inventory)
    output_state({"workflow_sources": inventory})


if __name__ == "__main__":
    main()
