from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import load_self_fix_target, lgwf_dir, output_state, write_json


ARTIFACT_ROOT = ".lgwf/prompt_acceptance"
PROMPT_REF_RE = re.compile(r'\b(PROMPT|PROMPT_REF)\s+"([^"]+\.md)"')
NODE_RE = re.compile(r"^\s*(PY|CODEX|APPROVAL|REACT|STEP)\s+([A-Za-z0-9_]+)")
PHASE_RE = re.compile(r"^\s*(REASON|ACT|OBSERVE)\s+")


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


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


def build_prompt_inventory(target_workflow_lgwf: Path) -> dict[str, Any]:
    target_workflow_lgwf = target_workflow_lgwf.resolve()
    package_root = target_workflow_lgwf.parent
    prompts: dict[str, dict[str, Any]] = {}
    for workflow in sorted(package_root.rglob("workflow.lgwf")):
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


def prompt_rules_text() -> str:
    base = Path.home() / ".codex" / "skills" / "lgwf-client-assist" / "references" / "prompt-assist"
    parts = []
    for name in ("guide.md", "prompt-audit-checklist.md", "shared-rules.md"):
        path = base / name
        if path.exists():
            parts.append(f"# {name}\n\n{path.read_text(encoding='utf-8', errors='replace')}")
    return "\n\n---\n\n".join(parts)


def main() -> None:
    target = load_self_fix_target()
    workflow = Path(str(target.get("target_workflow_lgwf", "")))
    if not workflow.exists():
        raise FileNotFoundError(f"target workflow.lgwf not found: {workflow}")
    out_dir = lgwf_dir() / "prompt_acceptance"
    inventory = build_prompt_inventory(workflow)
    write_json(out_dir / "inventory.json", inventory)
    (out_dir / "lgwf_prompt_rules.md").write_text(prompt_rules_text(), encoding="utf-8")
    output_state(
        {
            "prompt_inventory": inventory,
            "prompt_acceptance_artifact_root": ARTIFACT_ROOT,
        }
    )


if __name__ == "__main__":
    main()
