from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, read_json, repo_rel_or_abs, write_json, output_state, workflow_name_from_text


NODE_RE = re.compile(r"^\s*(PY|CODEX|APPROVAL|REACT|AGENT_LOOP|STEP|ROUTE)\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
FLOW_RE = re.compile(r"^\s*FLOW\s+([A-Za-z_][A-Za-z0-9_]*)(.*?)(?=^\s*(?:FLOW|ROUTE|PY|CODEX|APPROVAL|REACT|AGENT_LOOP|STEP)\s+|\Z)", re.MULTILINE | re.DOTALL)
WHEN_RE = re.compile(r'WHEN\s+"([^"]+)"\s+THEN\s+([A-Za-z_][A-Za-z0-9_]*)')
OUTPUT_JSON_RE = re.compile(r'OUTPUT_JSON\s+"([^"]+)"')
PERSIST_RE = re.compile(r'PERSIST\s+"([^"]+)"')
SCRIPT_RE = re.compile(r'SCRIPT\s+"([^"]+)"')
PROMPT_RE = re.compile(r'PROMPT(?:_REF)?\s+"([^"]+)"')
WORKFLOW_REF_RE = re.compile(r'WORKFLOW\s+"([^"]+)"')
THEN_RE = re.compile(r"\bTHEN\s+([A-Za-z_][A-Za-z0-9_]*)")


def parse_file(path: Path, root: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    nodes = []
    for match in NODE_RE.finditer(text):
        kind, node_id = match.groups()
        nodes.append({"id": node_id, "kind": kind, "workflow": repo_rel_or_abs(path, root)})
    flows = []
    for match in FLOW_RE.finditer(text):
        start = match.group(1)
        body = match.group(2)
        chain = [start, *THEN_RE.findall(body)]
        if len(chain) > 1:
            flows.append({"workflow": repo_rel_or_abs(path, root), "chain": chain})
    routes = []
    for route_match in re.finditer(r"^\s*ROUTE\s+([A-Za-z_][A-Za-z0-9_]*)(.*?)(?=^\s*(?:FLOW|ROUTE|PY|CODEX|APPROVAL|REACT|AGENT_LOOP|STEP)\s+|\Z)", text, re.MULTILINE | re.DOTALL):
        route_id, body = route_match.groups()
        routes.append(
            {
                "id": route_id,
                "workflow": repo_rel_or_abs(path, root),
                "branches": [{"value": value, "target": target} for value, target in WHEN_RE.findall(body)],
            }
        )
    return {
        "path": repo_rel_or_abs(path, root),
        "workflow_name": workflow_name_from_text(text),
        "nodes": nodes,
        "flows": flows,
        "routes": routes,
        "scripts": SCRIPT_RE.findall(text),
        "prompts": PROMPT_RE.findall(text),
        "workflow_refs": WORKFLOW_REF_RE.findall(text),
        "output_json": OUTPUT_JSON_RE.findall(text),
        "persist": PERSIST_RE.findall(text),
    }


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    root = Path(request["workflow_root"])
    sources = read_json(LGWF_DIR / "e2e_workflow_sources.json")
    files = [root / item["path"] for item in sources.get("workflows", [])]
    parsed = [parse_file(path, root) for path in files]
    graph = {
        "workflow_root": root.as_posix(),
        "workflow_name": request["workflow_name"],
        "workflows": parsed,
        "nodes": [node for item in parsed for node in item["nodes"]],
        "routes": [route for item in parsed for route in item["routes"]],
        "flows": [flow for item in parsed for flow in item["flows"]],
        "output_json": sorted({artifact for item in parsed for artifact in item["output_json"]}),
        "persist": sorted({artifact for item in parsed for artifact in item["persist"]}),
        "scripts": sorted({script for item in parsed for script in item["scripts"]}),
        "prompts": sorted({prompt for item in parsed for prompt in item["prompts"]}),
    }
    write_json(LGWF_DIR / "e2e_workflow_graph.json", graph)
    output_state({"workflow_graph": graph})


if __name__ == "__main__":
    main()
