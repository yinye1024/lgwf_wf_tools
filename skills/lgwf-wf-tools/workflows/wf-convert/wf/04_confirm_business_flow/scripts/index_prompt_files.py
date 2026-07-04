from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {".md", ".txt", ".prompt", ".json", ".yaml", ".yml", ".lgwf"}
SKIP_DIRS = {".git", ".lgwf", "__pycache__", ".pytest_cache", "node_modules"}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} must be a JSON object")
    return data


def build_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files: list[dict[str, Any]] = []
    workflow_files: list[str] = []
    prompt_candidates: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        relative = path.relative_to(root).as_posix()
        item = {
            "path": relative,
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        }
        files.append(item)
        if path.name == "workflow.lgwf":
            workflow_files.append(relative)
        if path.suffix.lower() in {".md", ".txt", ".prompt"}:
            prompt_candidates.append(relative)
    return {
        "root": str(root),
        "files": files,
        "workflow_files": workflow_files,
        "prompt_candidates": prompt_candidates,
    }


def main() -> None:
    work_root = Path.cwd()
    target = load_json(work_root / ".lgwf" / "prompt_convert_target.json")
    raw_target_dir = str(target.get("target_dir") or ".").strip()
    source_root = Path(raw_target_dir)
    if not source_root.is_absolute():
        source_root = (work_root / source_root).resolve()
    inventory = build_inventory(source_root)
    output_path = work_root / ".lgwf" / "prompt_file_index.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    for feedback_name in ("prompt_workflow_inspection_observe.json", "wf_create_input_observe.json"):
        feedback_path = output_path.parent / feedback_name
        if not feedback_path.exists():
            feedback_path.write_text(
                json.dumps({"verdict": "initial", "issues": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    proposal_path = output_path.parent / "wf_create_input_proposal.json"
    if not proposal_path.exists():
        proposal_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"lgwf_wf_convert.prompt_file_index": inventory}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
