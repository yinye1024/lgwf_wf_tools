from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import load_prompt_fix_target, lgwf_dir, output_state, write_json, write_prompt_fix_target


ARTIFACT_ROOT = ".lgwf/prompt_acceptance"
PROMPT_REF_RE = re.compile(r'\b(PROMPT|PROMPT_REF)\s+"([^"]+\.md)"')
NODE_RE = re.compile(r"^\s*(PY|CODEX|APPROVAL|REACT|STEP)\s+([A-Za-z0-9_]+)")
PHASE_RE = re.compile(r"^\s*(REASON|ACT|OBSERVE)\s+")
EXCLUDED_WORKFLOW_DIR_PARTS = {".git", ".lgwf", "__pycache__", "ws", "reports", "data"}


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_target_path(raw_path: str, workspace_root: Path | None = None) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    root = (workspace_root or Path.cwd()).resolve()
    for base in (root, *root.parents):
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate
    return (root / path).resolve()


def _nearest_node(lines: list[str], index: int) -> dict[str, str]:
    phase = ""
    for cursor in range(index, -1, -1):
        phase_match = PHASE_RE.match(lines[cursor])
        if phase_match and not phase:
            phase = phase_match.group(1).lower()
        node_match = NODE_RE.match(lines[cursor])
        if node_match:
            return {"node_type": node_match.group(1), "node_id": node_match.group(2), "react_phase": phase}
    return {"node_type": "", "node_id": "", "react_phase": phase}


def _prompt_excerpt(path: Path, limit: int = 4000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit]


def _should_skip_workflow(path: Path, package_root: Path) -> bool:
    try:
        relative_parts = path.resolve().relative_to(package_root.resolve()).parts
    except ValueError:
        return True
    return any(part in EXCLUDED_WORKFLOW_DIR_PARTS for part in relative_parts[:-1])


def build_prompt_inventory(target_workflow_lgwf: Path, target_package_root: Path | None = None) -> dict[str, Any]:
    target_workflow_lgwf = target_workflow_lgwf.resolve()
    package_root = (target_package_root or target_workflow_lgwf.parent).resolve()
    if not target_workflow_lgwf.is_relative_to(package_root):
        raise ValueError(f"target workflow.lgwf is outside target package root: {target_workflow_lgwf}")
    prompts: dict[str, dict[str, Any]] = {}
    for workflow in sorted(package_root.rglob("workflow.lgwf")):
        if _should_skip_workflow(workflow, package_root):
            continue
        lines = workflow.read_text(encoding="utf-8", errors="replace").splitlines()
        workflow_dir = workflow.parent
        for index, line in enumerate(lines):
            for match in PROMPT_REF_RE.finditer(line):
                raw_ref = match.group(2)
                prompt_path = (workflow_dir / raw_ref).resolve()
                try:
                    prompt_rel = _rel(prompt_path, package_root)
                    workflow_rel = _rel(workflow, package_root)
                except ValueError:
                    continue
                node = _nearest_node(lines, index)
                key = prompt_rel
                prompts[key] = {
                    "id": f"prompt_{len(prompts) + 1}",
                    "prompt_path": prompt_rel,
                    "workflow_path": workflow_rel,
                    "raw_ref": raw_ref,
                    "ref_kind": match.group(1),
                    "exists": prompt_path.exists(),
                    "node_type": node["node_type"],
                    "node_id": node["node_id"],
                    "react_phase": node["react_phase"],
                    "artifact_root": ARTIFACT_ROOT,
                    "excerpt": _prompt_excerpt(prompt_path),
                }
    return {
        "artifact_root": ARTIFACT_ROOT,
        "target_workflow_lgwf": str(target_workflow_lgwf),
        "target_package_root": str(package_root),
        "prompts": list(prompts.values()),
    }


def main() -> None:
    target = load_prompt_fix_target()
    workflow = resolve_target_path(str(target.get("target_workflow_lgwf", "")))
    if not workflow.exists():
        raise FileNotFoundError(f"target workflow.lgwf not found: {workflow}")
    package_root_value = target.get("target_package_root") or target.get("package_root")
    package_root = resolve_target_path(str(package_root_value)) if package_root_value else workflow.parent
    out_dir = lgwf_dir() / "prompt_acceptance"
    target = dict(target)
    target["target_workflow_lgwf"] = str(workflow.resolve())
    target["target_package_root"] = str(package_root.resolve())
    if "target_dirs" in target:
        target["target_dirs"] = [str(resolve_target_path(str(item))) for item in target["target_dirs"]]
    else:
        target["target_dirs"] = [str(package_root.resolve())]
    write_prompt_fix_target(target)
    inventory = build_prompt_inventory(workflow, package_root)
    write_json(out_dir / "inventory.json", inventory)
    output_state(
        {
            "prompt_fix_target": target,
            "target_dirs": target["target_dirs"],
            "prompt_inventory": inventory,
            "prompt_acceptance_artifact_root": ARTIFACT_ROOT,
        }
    )


if __name__ == "__main__":
    main()
