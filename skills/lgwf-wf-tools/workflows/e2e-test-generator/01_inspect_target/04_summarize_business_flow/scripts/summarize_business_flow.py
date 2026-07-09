from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def workflow_by_path(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("path") or "workflow.lgwf"): item
        for item in as_list(graph.get("workflows"))
        if isinstance(item, dict)
    }


def node_artifacts(workflows: dict[str, dict[str, Any]], workflow_path: str) -> list[str]:
    workflow = workflows.get(workflow_path) or {}
    artifacts = [
        *(str(item) for item in as_list(workflow.get("output_json"))),
        *(str(item) for item in as_list(workflow.get("persist"))),
    ]
    if artifacts:
        return sorted(set(artifacts))
    return []


def summarize_main_flow(graph: dict[str, Any]) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    for flow in as_list(graph.get("flows")):
        chain = [str(item) for item in as_list(flow.get("chain")) if str(item)]
        if chain:
            flows.append(
                {
                    "workflow": str(flow.get("workflow") or "workflow.lgwf"),
                    "chain": chain,
                    "start": chain[0],
                    "end": chain[-1],
                }
            )
    if flows:
        return flows
    nodes = [str(node.get("id") or "") for node in as_list(graph.get("nodes")) if node.get("id")]
    return [{"workflow": "workflow.lgwf", "chain": nodes, "start": nodes[0], "end": nodes[-1]}] if nodes else []


def approval_points(graph: dict[str, Any], workflows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in as_list(graph.get("nodes")):
        if str(node.get("kind") or "") != "APPROVAL":
            continue
        workflow = str(node.get("workflow") or "workflow.lgwf")
        result.append(
            {
                "node_id": str(node.get("id") or ""),
                "workflow": workflow,
                "persist_artifacts": [str(item) for item in as_list((workflows.get(workflow) or {}).get("persist"))],
                "test_implication": "runtime fake 和真实正向测试需要覆盖审批消费链。",
            }
        )
    return result


def route_points(graph: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for route in as_list(graph.get("routes")):
        branches = [
            {
                "value": str(branch.get("value") or ""),
                "target": str(branch.get("target") or ""),
            }
            for branch in as_list(route.get("branches"))
        ]
        points.append(
            {
                "route_id": str(route.get("id") or ""),
                "workflow": str(route.get("workflow") or "workflow.lgwf"),
                "branches": branches,
                "test_implication": "script_flow 和 runtime_fake 需要覆盖每个业务分支。",
            }
        )
    return points


def codex_artifacts(graph: dict[str, Any], workflows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in as_list(graph.get("nodes")):
        kind = str(node.get("kind") or "")
        if kind not in {"CODEX", "REACT", "AGENT_LOOP"}:
            continue
        workflow = str(node.get("workflow") or "workflow.lgwf")
        result.append(
            {
                "node_id": str(node.get("id") or ""),
                "kind": kind,
                "workflow": workflow,
                "artifacts": node_artifacts(workflows, workflow),
                "test_implication": "使用 fake response 或人工正向链路验证输出 artifact 契约。",
            }
        )
    return result


def risks(graph: dict[str, Any], approvals: list[dict[str, Any]], routes: list[dict[str, Any]], codex_nodes: list[dict[str, Any]]) -> list[str]:
    items: list[str] = []
    if codex_nodes:
        items.append("静态解析无法保证真实 Codex 输出语义，真实正向入口仍需人工显式执行。")
    if approvals:
        items.append("存在人工审批节点，测试必须区分 approval metadata 与业务 value。")
    if routes:
        items.append("存在业务分支，生成测试需要持续校验分支覆盖，避免消费链漏检。")
    if not as_list(graph.get("flows")):
        items.append("未解析到 FLOW 主链，只能按节点清单生成弱摘要。")
    return items


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    graph = read_json(LGWF_DIR / "e2e_workflow_graph.json")
    sources = read_json(LGWF_DIR / "e2e_workflow_sources.json", {})
    workflows = workflow_by_path(graph)
    main_flow = summarize_main_flow(graph)
    approvals = approval_points(graph, workflows)
    routes = route_points(graph)
    codex_nodes = codex_artifacts(graph, workflows)

    workflow_name = str(request.get("workflow_name") or graph.get("workflow_name") or "target_workflow")
    summary = {
        "summary": f"{workflow_name} 包含 {len(as_list(graph.get('nodes')))} 个节点、{len(routes)} 个 route 和 {len(approvals)} 个审批点，测试生成应按脚本、runtime fake、真实正向和 wf-fix 正向分层覆盖。",
        "main_flow": main_flow,
        "approval_points": approvals,
        "route_points": routes,
        "codex_artifacts": codex_nodes,
        "test_focus": {
            "script_flow": [
                "验证 PY SCRIPT 文件存在、可编译，并覆盖 ROUTE/PERSIST 声明。",
                "不启动目标 runtime，不调用真实 Codex。",
            ],
            "runtime_fake": [
                "使用 Python fake Codex 与 --prompt-file 契约覆盖 runtime 驱动、状态查询和审批命令。",
                "按 coverage matrix 覆盖业务 route 分支和关键 artifact。",
            ],
            "real_positive": [
                "保留人工显式执行入口，用真实 Codex 验证主业务闭环和目标 workflow audit。",
            ],
            "wf_fix_positive": [
                "复用真实正向场景作为 wf-fix 目标，验证修复入口和 artifact 留存契约。",
            ],
        },
        "risks": risks(graph, approvals, routes, codex_nodes),
        "source_counts": {
            "workflow_files": len(as_list(sources.get("workflows"))),
            "script_files": len(as_list(sources.get("scripts"))),
            "prompt_files": len(as_list(sources.get("prompts"))),
        },
    }
    write_json(LGWF_DIR / "e2e_business_flow_summary.json", summary)
    output_state({"business_flow_summary": summary})


if __name__ == "__main__":
    main()
