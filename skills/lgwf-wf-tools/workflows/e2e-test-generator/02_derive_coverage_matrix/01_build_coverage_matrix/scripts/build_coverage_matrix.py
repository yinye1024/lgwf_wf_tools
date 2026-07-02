from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json


REPAIR_RETRY_KEYWORDS = ("retry", "repair", "continue", "fix")


def flatten_routes(graph_routes: list[dict]) -> list[dict]:
    routes = []
    for route in graph_routes:
        for branch in route.get("branches", []):
            routes.append({"route_id": route["id"], **branch, "workflow": route["workflow"]})
    return routes


def branch_targets(graph_routes: list[dict]) -> list[dict]:
    targets = []
    seen: set[tuple[str, str, str, str]] = set()
    for route in graph_routes:
        for branch in route.get("branches", []):
            item = {
                "route_id": route["id"],
                "value": branch["value"],
                "target": branch["target"],
                "workflow": route["workflow"],
            }
            key = (item["route_id"], item["value"], item["target"], item["workflow"])
            if key not in seen:
                seen.add(key)
                targets.append(item)
    return targets


def repair_or_retry_nodes(nodes: list[dict], branches: list[dict]) -> list[dict]:
    nodes_by_id = {node["id"]: node for node in nodes}
    candidates: dict[str, dict] = {}

    def add(node_id: str, reason: str) -> None:
        node = nodes_by_id.get(node_id)
        if not node or node["kind"] not in {"REACT", "AGENT_LOOP"}:
            return
        item = dict(node)
        item["reason"] = reason
        candidates[node_id] = item

    for node in nodes:
        node_id = node["id"]
        if node["kind"] in {"REACT", "AGENT_LOOP"} and any(keyword in node_id.lower() for keyword in REPAIR_RETRY_KEYWORDS):
            add(node_id, "node_id_keyword")

    for branch in branches:
        value = branch["value"].lower()
        target = branch["target"].lower()
        if any(keyword in value or keyword in target for keyword in REPAIR_RETRY_KEYWORDS):
            add(branch["target"], f"route_branch:{branch['route_id']}:{branch['value']}")

    return sorted(candidates.values(), key=lambda item: item["id"])


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    graph = read_json(LGWF_DIR / "e2e_workflow_graph.json")
    routes = flatten_routes(graph.get("routes", []))
    runtime_branch_targets = branch_targets(graph.get("routes", []))
    selected = set(request.get("selected_test_types") or ["script_flow", "runtime_fake", "real_positive", "wf_fix_positive"])

    nodes_by_kind: dict[str, list[dict]] = {}
    for node in graph.get("nodes", []):
        nodes_by_kind.setdefault(node["kind"], []).append(node)

    matrix = {
        "target": {
            "workflow_name": request["workflow_name"],
            "test_name_prefix": request["test_name_prefix"],
            "test_output_dir": request["test_output_dir"],
            "generated_tests": request["generated_tests"],
            "selected_test_types": request.get("selected_test_types", []),
        },
        "script_flow": {
            "selected": "script_flow" in selected,
            "goal": "覆盖脚本级分支和状态推进，不启动 workflow runtime。",
            "script_contracts": graph.get("scripts", []),
            "routes": routes,
            "approval_persist": graph.get("persist", []),
        },
        "runtime_fake": {
            "selected": "runtime_fake" in selected,
            "goal": "启动真实 LGWF runtime，使用 Python fake Codex 验证编排连通和关键分支。",
            "codex_like_nodes": nodes_by_kind.get("CODEX", []) + nodes_by_kind.get("REACT", []) + nodes_by_kind.get("AGENT_LOOP", []),
            "approval_nodes": nodes_by_kind.get("APPROVAL", []),
            "routes": routes,
            "flows": graph.get("flows", []),
            "output_json": graph.get("output_json", []),
            "persist_artifacts": graph.get("persist", []),
            "branch_targets": runtime_branch_targets,
            "repair_or_retry_nodes": repair_or_retry_nodes(graph.get("nodes", []), runtime_branch_targets),
        },
        "real_positive": {
            "selected": "real_positive" in selected,
            "goal": "真实 Codex 正向业务闭环，作为人工验收入口；文件名不使用 test_ 前缀，默认不纳入 unittest discover。",
            "main_flows": graph.get("flows", []),
            "black_box_outputs": graph.get("output_json", []),
            "manual_run_command": f"python {request['test_output_dir']}/{request['generated_tests']['real_positive']}",
            "discover_collected": False,
        },
        "wf_fix_positive": {
            "selected": "wf_fix_positive" in selected,
            "goal": "复用真实正向场景启动 wf-fix，驱动目标 workflow 边跑边修复，作为人工验收入口。",
            "target_workflow_lgwf": request["workflow_lgwf"],
            "scenario_source": ".lgwf/e2e_real_positive_design.json",
            "max_attempts": 5,
            "ask_main_agent_for_target_approvals": True,
            "manual_run_command": f"python {request['test_output_dir']}/{request['generated_tests']['wf_fix_positive']}",
            "discover_collected": False,
        },
    }
    write_json(LGWF_DIR / "e2e_coverage_matrix.json", matrix)
    output_state({"coverage_matrix": matrix})


if __name__ == "__main__":
    main()
