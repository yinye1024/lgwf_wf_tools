from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    graph = read_json(LGWF_DIR / "e2e_workflow_graph.json")
    routes = []
    for route in graph.get("routes", []):
        for branch in route.get("branches", []):
            routes.append({"route_id": route["id"], **branch, "workflow": route["workflow"]})

    nodes_by_kind: dict[str, list[dict]] = {}
    for node in graph.get("nodes", []):
        nodes_by_kind.setdefault(node["kind"], []).append(node)

    matrix = {
        "target": {
            "workflow_name": request["workflow_name"],
            "test_name_prefix": request["test_name_prefix"],
            "test_output_dir": request["test_output_dir"],
            "generated_tests": request["generated_tests"],
            "real_codex_env": request["real_codex_env"],
        },
        "script_flow": {
            "goal": "覆盖脚本级分支和状态推进，不启动 workflow runtime。",
            "script_contracts": graph.get("scripts", []),
            "routes": routes,
            "approval_persist": graph.get("persist", []),
        },
        "runtime_fake": {
            "goal": "启动真实 LGWF runtime，使用 Python fake Codex 验证编排连通。",
            "codex_like_nodes": nodes_by_kind.get("CODEX", []) + nodes_by_kind.get("REACT", []) + nodes_by_kind.get("AGENT_LOOP", []),
            "output_json": graph.get("output_json", []),
            "approval_nodes": nodes_by_kind.get("APPROVAL", []),
        },
        "real_positive": {
            "goal": "真实 Codex 正向业务闭环，默认跳过。",
            "main_flows": graph.get("flows", []),
            "black_box_outputs": graph.get("output_json", []),
            "skip_env": request["real_codex_env"],
        },
    }
    write_json(LGWF_DIR / "e2e_coverage_matrix.json", matrix)
    output_state({"coverage_matrix": matrix})


if __name__ == "__main__":
    main()
