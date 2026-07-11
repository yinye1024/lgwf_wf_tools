from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, slugify, write_json


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def unique_items(items: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for item in items:
        key = tuple(str(item.get(field) or "") for field in fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def graph_nodes(graph: dict[str, Any], kinds: set[str]) -> list[dict[str, str]]:
    nodes: list[dict[str, str]] = []
    for node in as_list(graph.get("nodes")):
        kind = str(node.get("kind") or "")
        if kind in kinds:
            nodes.append(
                {
                    "id": str(node.get("id") or ""),
                    "kind": kind,
                    "workflow": str(node.get("workflow") or "workflow.lgwf"),
                }
            )
    return unique_items(nodes, ("id", "kind", "workflow"))


def node_entries(runtime: dict[str, Any], graph: dict[str, Any], key: str, kinds: set[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for node in as_list(runtime.get(key)):
        entries.append(
            {
                "id": str(node.get("id") or ""),
                "kind": str(node.get("kind") or ""),
                "workflow": str(node.get("workflow") or "workflow.lgwf"),
            }
        )
    if not entries:
        entries = graph_nodes(graph, kinds)
    return unique_items([entry for entry in entries if entry["id"]], ("id", "kind", "workflow"))


def normalize_route(item: dict[str, Any], route_id: str | None = None, workflow: str | None = None) -> dict[str, str]:
    return {
        "route_id": str(item.get("route_id") or item.get("id") or route_id or ""),
        "value": str(item.get("value") or ""),
        "target": str(item.get("target") or ""),
        "workflow": str(item.get("workflow") or workflow or "workflow.lgwf"),
    }


def route_entries(runtime: dict[str, Any], graph: dict[str, Any]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for key in ("branch_targets", "routes"):
        for route in as_list(runtime.get(key)):
            routes.append(normalize_route(route))
    if not routes:
        for route in as_list(graph.get("routes")):
            route_id = str(route.get("id") or "")
            workflow = str(route.get("workflow") or "workflow.lgwf")
            for branch in as_list(route.get("branches")):
                routes.append(normalize_route(branch, route_id=route_id, workflow=workflow))
    routes = [
        route
        for route in routes
        if route["route_id"] and route["value"] and route["target"] and route["workflow"]
    ]
    return unique_items(routes, ("route_id", "value", "target", "workflow"))


def string_list(value: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in as_list(value):
        text = str(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def scenario_id(base: str, used: set[str]) -> str:
    candidate = slugify(base)
    if candidate not in used:
        used.add(candidate)
        return candidate
    index = 2
    while f"{candidate}_{index}" in used:
        index += 1
    final = f"{candidate}_{index}"
    used.add(final)
    return final


def fake_responses(codex_nodes: list[dict[str, str]], output_json: list[str]) -> list[dict[str, Any]]:
    responses: list[dict[str, Any]] = []
    for index, node in enumerate(codex_nodes):
        target_artifact = output_json[index] if index < len(output_json) else ".lgwf/fake_codex_output.json"
        responses.append(
            {
                "node_id": node["id"],
                "workflow": node["workflow"],
                "prompt_file_required": True,
                "response_json": {"ok": True, "node": node["id"], "artifact": target_artifact},
                "expected_artifact": target_artifact,
            }
        )
    return responses


def repair_plan(repair_context: dict[str, Any]) -> list[dict[str, str]]:
    plan: list[dict[str, str]] = []
    for blocker in as_list(repair_context.get("blockers")):
        plan.append(
            {
                "issue_code": str(blocker.get("issue_code") or ""),
                "target": str(blocker.get("target") or ""),
                "source": str(blocker.get("source") or ""),
                "planned_action": str(blocker.get("repair_hint") or "重新生成 deterministic runtime fake 合约测试。"),
            }
        )
    return plan


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    graph = read_json(LGWF_DIR / "e2e_workflow_graph.json", {})
    matrix = read_json(LGWF_DIR / "e2e_coverage_matrix.json")
    repair_context = read_json(LGWF_DIR / "e2e_runtime_fake_repair_context.json", {})
    runtime = matrix.get("runtime_fake") or {}
    selected = bool(runtime.get("selected", True))
    test_file = f"{request['test_output_dir'].strip('/')}/{request['generated_tests']['runtime_fake']}"

    codex_nodes = node_entries(runtime, graph, "codex_like_nodes", {"CODEX", "REACT"})
    approval_nodes = node_entries(runtime, graph, "approval_nodes", {"APPROVAL"})
    routes = route_entries(runtime, graph)
    output_json = string_list(runtime.get("output_json") or graph.get("output_json"))
    persist_artifacts = string_list(runtime.get("persist_artifacts") or graph.get("persist"))
    repair_nodes = node_entries(runtime, graph, "repair_or_retry_nodes", {"REACT"})

    warnings: list[str] = []
    scenarios: list[dict[str, Any]] = []
    coverage_claims: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    if not selected:
        warnings.append("runtime_fake 未被 selected_test_types 选中，跳过生成。")
    else:
        terminal_routes = [
            route
            for route in routes
            if route["value"].lower() in {"done", "success", "ok", "approve", "approved", "exit", "complete"}
        ]
        happy_branches = terminal_routes[:1] or routes[:1]
        scenarios.append(
            {
                "scenario_id": scenario_id("happy_path", used_ids),
                "goal": "验证 runtime + Python fake Codex 的主线编排契约，包括 prompt-file、状态查询和审批命令模板。",
                "expected_runtime_path": [
                    *(node["id"] for node in codex_nodes[:1]),
                    *(node["id"] for node in approval_nodes[:1]),
                    *(branch["target"] for branch in happy_branches),
                ],
                "manual_approval_required": bool(approval_nodes),
                "approval_decisions": [
                    {"node_id": node["id"], "decision": "approve", "value": {}}
                    for node in approval_nodes
                ],
                "fake_responses": fake_responses(codex_nodes, output_json),
                "covered_branches": happy_branches,
                "covered_artifacts": [*output_json, *persist_artifacts],
            }
        )
        coverage_claims.append(
            {
                "coverage_ref": "runtime_driver_contract",
                "scenario_ids": ["happy_path"],
                "claim": "覆盖 lgwf.py run、--prompt-file、status、approval get/submit 与 Python fake Codex 基础契约。",
            }
        )

        for route in routes:
            sid = scenario_id(f"route_{route['route_id']}_{route['value']}", used_ids)
            scenarios.append(
                {
                    "scenario_id": sid,
                    "goal": f"覆盖 ROUTE {route['route_id']} 的 {route['value']} 分支。",
                    "expected_runtime_path": [route["target"]],
                    "manual_approval_required": bool(approval_nodes),
                    "approval_decisions": [
                        {"node_id": node["id"], "decision": "approve", "value": {}}
                        for node in approval_nodes
                    ],
                    "fake_responses": fake_responses(codex_nodes, output_json),
                    "covered_branches": [route],
                    "covered_artifacts": [*output_json, *persist_artifacts],
                }
            )
            coverage_claims.append(
                {
                    "coverage_ref": f"route:{route['route_id']}:{route['value']}",
                    "scenario_ids": [sid],
                    "claim": "覆盖 business route 分支声明与生成测试方法映射。",
                }
            )

        if approval_nodes:
            sid = scenario_id("manual_approval_required", used_ids)
            scenarios.append(
                {
                    "scenario_id": sid,
                    "goal": "验证 runtime fake 测试包含 approval get 与 approval submit 决策链。",
                    "expected_runtime_path": [node["id"] for node in approval_nodes],
                    "manual_approval_required": True,
                    "approval_decisions": [
                        {"node_id": node["id"], "decision": "approve", "value": {}}
                        for node in approval_nodes
                    ],
                    "fake_responses": fake_responses(codex_nodes, output_json),
                    "covered_branches": [],
                    "covered_artifacts": persist_artifacts,
                }
            )
            coverage_claims.append(
                {
                    "coverage_ref": "manual_approval_required",
                    "scenario_ids": [sid],
                    "claim": "覆盖人工确认命令链，不把审批元数据误写为业务 value。",
                }
            )
        else:
            warnings.append("未识别到 APPROVAL 节点，runtime fake 测试只保留 approval 命令模板静态契约。")

        if repair_nodes:
            sid = scenario_id("repair_or_retry_contract", used_ids)
            scenarios.append(
                {
                    "scenario_id": sid,
                    "goal": "验证 repair/retry 节点不会回到错误的前序 Codex repair loop。",
                    "expected_runtime_path": [node["id"] for node in repair_nodes],
                    "manual_approval_required": bool(approval_nodes),
                    "approval_decisions": [],
                    "fake_responses": fake_responses(codex_nodes, output_json),
                    "covered_branches": [],
                    "covered_artifacts": output_json,
                }
            )
            coverage_claims.append(
                {
                    "coverage_ref": "repair_or_retry_nodes",
                    "scenario_ids": [sid],
                    "claim": "覆盖 retry/repair 节点的稳定路径声明。",
                }
            )

    design = {
        "test_file": test_file,
        "purpose": "runtime fake E2E 合约测试生成，不调用真实 Codex。",
        "selected": selected,
        "workflow_root": request["workflow_root"],
        "workflow_lgwf": request["workflow_lgwf"],
        "runtime_driver": {
            "run_command": "lgwf.py run --workflow-lgwf {workflow_lgwf} --work-dir {work_dir} --prompt-file {prompt_file}",
            "status_command": "lgwf.py status --pid {pid}",
            "approval_commands": [
                "lgwf.py approval get --pid {pid}",
                "lgwf.py approval submit --pid {pid} --decision approve",
            ],
        },
        "fake_codex_contract": {
            "implementation": "Python fake Codex",
            "class_name": "FakeCodex",
            "prompt_file_support": True,
            "call_index": True,
            "response_mapping": fake_responses(codex_nodes, output_json),
        },
        "codex_like_nodes": codex_nodes,
        "approval_nodes": approval_nodes,
        "branch_targets": routes,
        "artifact_assertions": {
            "output_json": output_json,
            "persist_artifacts": persist_artifacts,
        },
        "scenarios": scenarios,
        "coverage_claims": coverage_claims,
        "repair_plan": repair_plan(repair_context),
        "repair_context": {
            "active": bool(repair_context.get("active")),
            "history_count": int(repair_context.get("history_count") or repair_context.get("attempt") or 0),
            "no_progress": bool(repair_context.get("no_progress")),
        },
        "design_warnings": warnings,
    }
    write_json(LGWF_DIR / "e2e_runtime_fake_design.json", design)
    output_state({"runtime_fake_design": design})


if __name__ == "__main__":
    main()
