from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json


def workflow_items(graph: dict[str, Any]) -> list[dict[str, Any]]:
    items = graph.get("workflows")
    return items if isinstance(items, list) else []


def script_entries(graph: dict[str, Any], matrix: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for workflow in workflow_items(graph):
        workflow_path = str(workflow.get("path") or "workflow.lgwf")
        workflow_dir = Path(workflow_path).parent
        for script in workflow.get("scripts") or []:
            script_path = str(script)
            resolved = (workflow_dir / script_path).as_posix()
            key = (workflow_path, resolved)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "workflow": workflow_path,
                    "script_path": script_path,
                    "resolved_path": resolved,
                }
            )
    if entries:
        return entries

    for script in matrix.get("script_contracts") or []:
        script_path = str(script)
        entries.append(
            {
                "workflow": "workflow.lgwf",
                "script_path": script_path,
                "resolved_path": script_path,
            }
        )
    return entries


def route_entries(graph: dict[str, Any], matrix: dict[str, Any]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for route in matrix.get("routes") or []:
        item = {
            "route_id": str(route.get("route_id") or route.get("id") or ""),
            "value": str(route.get("value") or ""),
            "target": str(route.get("target") or ""),
            "workflow": str(route.get("workflow") or "workflow.lgwf"),
        }
        key = (item["route_id"], item["value"], item["target"], item["workflow"])
        if all(key) and key not in seen:
            seen.add(key)
            routes.append(item)
    if routes:
        return routes

    for route in graph.get("routes") or []:
        route_id = str(route.get("id") or "")
        workflow_path = str(route.get("workflow") or "workflow.lgwf")
        for branch in route.get("branches") or []:
            item = {
                "route_id": route_id,
                "value": str(branch.get("value") or ""),
                "target": str(branch.get("target") or ""),
                "workflow": workflow_path,
            }
            key = (item["route_id"], item["value"], item["target"], item["workflow"])
            if all(key) and key not in seen:
                seen.add(key)
                routes.append(item)
    return routes


def approval_entries(graph: dict[str, Any], matrix: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for workflow in workflow_items(graph):
        workflow_path = str(workflow.get("path") or "workflow.lgwf")
        for artifact in workflow.get("persist") or []:
            key = (workflow_path, str(artifact))
            if key not in seen:
                seen.add(key)
                entries.append({"workflow": workflow_path, "artifact": str(artifact)})
    if entries:
        return entries

    for artifact in matrix.get("approval_persist") or []:
        key = ("workflow.lgwf", str(artifact))
        if key not in seen:
            seen.add(key)
            entries.append({"workflow": "workflow.lgwf", "artifact": str(artifact)})
    return entries


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    graph = read_json(LGWF_DIR / "e2e_workflow_graph.json", {})
    matrix = read_json(LGWF_DIR / "e2e_coverage_matrix.json")
    script_flow = matrix.get("script_flow") or {}
    selected = bool(script_flow.get("selected", True))
    test_file = f"{request['test_output_dir'].strip('/')}/{request['generated_tests']['script_flow']}"

    scripts = script_entries(graph, script_flow)
    routes = route_entries(graph, script_flow)
    approvals = approval_entries(graph, script_flow)
    workflow_files = sorted(
        {
            *(str(item.get("path") or "workflow.lgwf") for item in workflow_items(graph)),
            *(entry["workflow"] for entry in routes),
            *(entry["workflow"] for entry in approvals),
        }
    )
    if not workflow_files:
        workflow_files = ["workflow.lgwf"]

    cases: list[dict[str, Any]] = []
    coverage_claims: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not selected:
        warnings.append("script_flow 未被 selected_test_types 选中，跳过脚本级测试生成。")
    else:
        if scripts:
            cases.append(
                {
                    "case_id": "case_script_contracts_compile",
                    "goal": "验证 workflow 声明的 PY SCRIPT 文件存在且可通过 py_compile。",
                    "preconditions": ["目标 workflow package 已扫描完成。"],
                    "state_files": [
                        {
                            "path": ".lgwf/e2e_workflow_graph.json",
                            "purpose": "提供 workflow 到脚本文件的相对路径映射。",
                            "required_fields": ["workflows[].path", "workflows[].scripts[]"],
                        }
                    ],
                    "script_calls": scripts,
                    "route_assertions": [],
                    "artifact_assertions": ["每个 resolved_path 都存在且可编译。"],
                    "forbidden_assertions": ["不得启动 LGWF runtime。", "不得调用真实模型 CLI。"],
                    "coverage_refs": ["script_contracts"],
                }
            )
            coverage_claims.append(
                {
                    "coverage_ref": "script_contracts",
                    "case_ids": ["case_script_contracts_compile"],
                    "claim": "覆盖 coverage matrix 中的脚本契约存在性与 Python 编译检查。",
                }
            )
        else:
            warnings.append("未识别到 script_contracts，脚本级测试无法覆盖脚本直调契约。")

        if routes:
            cases.append(
                {
                    "case_id": "case_routes_declared",
                    "goal": "验证 coverage matrix 中列出的 ROUTE 分支仍存在于对应 workflow.lgwf。",
                    "preconditions": ["目标 workflow source 可读。"],
                    "state_files": [
                        {
                            "path": ".lgwf/e2e_coverage_matrix.json",
                            "purpose": "提供 route_id、value、target 和 workflow 映射。",
                            "required_fields": ["script_flow.routes[]"],
                        }
                    ],
                    "script_calls": [],
                    "route_assertions": [
                        f'{route["workflow"]}: WHEN "{route["value"]}" THEN {route["target"]}'
                        for route in routes
                    ],
                    "artifact_assertions": [],
                    "forbidden_assertions": ["不得启动 LGWF runtime。"],
                    "coverage_refs": [f'route:{route["route_id"]}:{route["value"]}' for route in routes],
                }
            )
            coverage_claims.extend(
                {
                    "coverage_ref": f'route:{route["route_id"]}:{route["value"]}',
                    "case_ids": ["case_routes_declared"],
                    "claim": "覆盖 ROUTE 分支声明存在性。",
                }
                for route in routes
            )
        else:
            warnings.append("未识别到 ROUTE 分支，脚本级测试不会生成 route 断言。")

        if approvals:
            cases.append(
                {
                    "case_id": "case_approval_persist_declared",
                    "goal": "验证审批持久化 artifact 仍由 workflow 声明。",
                    "preconditions": ["目标 workflow source 可读。"],
                    "state_files": [
                        {
                            "path": ".lgwf/e2e_coverage_matrix.json",
                            "purpose": "提供 approval persist artifact 清单。",
                            "required_fields": ["script_flow.approval_persist[]"],
                        }
                    ],
                    "script_calls": [],
                    "route_assertions": [],
                    "artifact_assertions": [
                        f'{entry["workflow"]}: PERSIST "{entry["artifact"]}"' for entry in approvals
                    ],
                    "forbidden_assertions": ["不得提交真实审批。"],
                    "coverage_refs": [f'approval_persist:{entry["artifact"]}' for entry in approvals],
                }
            )
            coverage_claims.extend(
                {
                    "coverage_ref": f'approval_persist:{entry["artifact"]}',
                    "case_ids": ["case_approval_persist_declared"],
                    "claim": "覆盖审批持久化 artifact 声明存在性。",
                }
                for entry in approvals
            )
        else:
            warnings.append("未识别到 approval persist artifact，脚本级测试不会生成审批持久化断言。")

        cases.append(
            {
                "case_id": "case_no_runtime_or_model_launch_guard",
                "goal": "验证生成的脚本级测试自身不包含 runtime 或真实模型启动入口。",
                "preconditions": ["测试文件已生成。"],
                "state_files": [
                    {
                        "path": ".lgwf/e2e_script_flow_generation.json",
                        "purpose": "记录生成文件与 guard 机制。",
                        "required_fields": ["test_file", "guard_mechanisms[]"],
                    }
                ],
                "script_calls": [],
                "route_assertions": [],
                "artifact_assertions": ["测试文件源码不包含 runtime/model 启动命令字面量。"],
                "forbidden_assertions": ["lgwf.py run", "--workflow-lgwf", "codex"],
                "coverage_refs": ["forbidden_patterns"],
            }
        )
        coverage_claims.append(
            {
                "coverage_ref": "forbidden_patterns",
                "case_ids": ["case_no_runtime_or_model_launch_guard"],
                "claim": "覆盖脚本级测试不得启动 runtime 或真实模型的反向约束。",
            }
        )

    design = {
        "test_file": test_file,
        "purpose": "脚本级全分支覆盖，不启动 runtime",
        "selected": selected,
        "workflow_root": request["workflow_root"],
        "workflow_files": workflow_files,
        "script_entries": scripts,
        "route_entries": routes,
        "approval_persist_entries": approvals,
        "cases": cases,
        "required_helpers": [
            {
                "helper_name": "workflow_text",
                "purpose": "读取目标 workflow.lgwf 文本并进行声明级断言。",
                "case_ids": ["case_routes_declared", "case_approval_persist_declared"],
            },
            {
                "helper_name": "compile_script",
                "purpose": "用 py_compile 编译目标脚本文件。",
                "case_ids": ["case_script_contracts_compile"],
            },
        ],
        "forbidden_patterns": ["lgwf.py run", "--workflow-lgwf", "codex"],
        "coverage_claims": coverage_claims,
        "design_warnings": warnings,
    }
    write_json(LGWF_DIR / "e2e_script_flow_design.json", design)
    output_state({"script_flow_design": design})


if __name__ == "__main__":
    main()
