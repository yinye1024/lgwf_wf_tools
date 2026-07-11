from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = PACKAGE_ROOT.parents[1]
LGWF = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def load_module(relative_path: str, module_name: str):
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegistryContractTests(unittest.TestCase):
    def test_registry_declares_wf_post_fix_as_lgwf_workflow(self) -> None:
        registry = json.loads((FACADE_ROOT / "registry.json").read_text(encoding="utf-8"))
        workflows = {item["id"]: item for item in registry["workflows"]}

        self.assertEqual(
            {
                "id": "wf-post-fix",
                "kind": "lgwf",
                "description": "对目标 LGWF workflow 执行 prompt 修复、prompt 升级、E2E 生成和可选验收运行。",
                "workflow_lgwf": "workflows/wf-post-fix/wf/workflow.lgwf",
                "work_dir": "workflows/wf-post-fix/ws",
                "agents_md": "workflows/wf-post-fix/AGENTS.md",
                "entry_contract": "workflows/wf-post-fix/entry_contract.json",
            },
            workflows["wf-post-fix"],
        )


class WorkflowShapeTests(unittest.TestCase):
    def compile_workflow(self, workflow_lgwf: Path) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "workflow.json"
            completed = subprocess.run(
                [sys.executable, str(LGWF), "compile", str(workflow_lgwf), "--output", str(output)],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            return json.loads(output.read_text(encoding="utf-8"))

    def test_root_workflow_keeps_run_workflow_inside_stage_workflows(self) -> None:
        text = (PACKAGE_ROOT / "wf/workflow.lgwf").read_text(encoding="utf-8")

        self.assertNotIn("RUN_WORKFLOW", text)
        self.assertIn("ENTRY FLOW main", text)
        self.assertIn("FLOW main", text)
        self.assertIn("START prepare_target", text)
        self.assertNotIn("FLOW {", text)
        self.assertIn('WORKFLOW "02_audit_fix/workflow.lgwf"', text)
        self.assertIn('WORKFLOW "02_prompt_fix/workflow.lgwf"', text)
        self.assertIn('WORKFLOW "03_prompt_upgrade/workflow.lgwf"', text)
        self.assertIn('WORKFLOW "04_e2e_generate/workflow.lgwf"', text)
        self.assertNotIn("ROUTE prompt_fix_stage", text)

        audit_fix_text = (PACKAGE_ROOT / "wf/02_audit_fix/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE audit_fix_auto_route", audit_fix_text)
        self.assertIn("ROUTE audit_fix_auto_route", audit_fix_text)
        self.assertIn("READ state.lgwf_wf_post_fix.post_fix_decisions.auto_enabled", audit_fix_text)
        self.assertIn("WHEN true THEN auto_audit_fix_flow", audit_fix_text)
        self.assertIn("WHEN false THEN choose_audit_fix", audit_fix_text)
        self.assertIn("CHOICE choose_audit_fix", audit_fix_text)
        self.assertIn('OPTION run LABEL "运行 audit 修复" THEN run_audit_fix_flow', audit_fix_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行 audit 修复" THEN auto_audit_fix_flow', audit_fix_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', audit_fix_text)
        self.assertIn("FLOW auto_audit_fix_flow", audit_fix_text)
        self.assertIn("RUN_WORKFLOW audit_fix", audit_fix_text)
        self.assertIn('WORKFLOW "workflows/wf-audit-fix/wf/workflow.lgwf"', audit_fix_text)

        prompt_fix_text = (PACKAGE_ROOT / "wf/02_prompt_fix/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE prompt_fix_auto_route", prompt_fix_text)
        self.assertIn("ROUTE prompt_fix_auto_route", prompt_fix_text)
        self.assertIn("READ state.lgwf_wf_post_fix.post_fix_decisions.auto_enabled", prompt_fix_text)
        self.assertIn("WHEN true THEN auto_prompt_fix_flow", prompt_fix_text)
        self.assertNotIn("WHEN true THEN run_prompt_fix_flow", prompt_fix_text)
        self.assertIn("WHEN false THEN choose_prompt_fix", prompt_fix_text)
        self.assertIn("CHOICE choose_prompt_fix", prompt_fix_text)
        self.assertNotIn("ROUTES {", prompt_fix_text)
        self.assertIn('OPTION run LABEL "运行 prompt 修复" THEN run_prompt_fix_flow', prompt_fix_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行 prompt 修复" THEN auto_prompt_fix_flow', prompt_fix_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', prompt_fix_text)
        self.assertIn("FLOW auto_prompt_fix_flow", prompt_fix_text)
        self.assertIn("START set_prompt_fix_auto", prompt_fix_text)
        self.assertNotIn('ROUTE choose_prompt_fix', prompt_fix_text)
        self.assertNotIn("ROUTE prepare_prompt_fix_decision", prompt_fix_text)
        self.assertNotIn("PY auto_gate_prompt_fix", prompt_fix_text)
        self.assertIn("RUN_WORKFLOW prompt_fix", prompt_fix_text)
        self.assertIn('WORKFLOW "workflows/wf-prompt-fix/wf/workflow.lgwf"', prompt_fix_text)

        prompt_upgrade_text = (PACKAGE_ROOT / "wf/03_prompt_upgrade/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE prompt_upgrade_auto_route", prompt_upgrade_text)
        self.assertIn("ROUTE prompt_upgrade_auto_route", prompt_upgrade_text)
        self.assertIn("WHEN true THEN auto_prompt_upgrade_flow", prompt_upgrade_text)
        self.assertNotIn("WHEN true THEN run_prompt_upgrade_flow", prompt_upgrade_text)
        self.assertIn("CHOICE choose_prompt_upgrade", prompt_upgrade_text)
        self.assertNotIn("ROUTES {", prompt_upgrade_text)
        self.assertIn('OPTION run LABEL "运行 prompt 升级" THEN run_prompt_upgrade_flow', prompt_upgrade_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行 prompt 升级" THEN auto_prompt_upgrade_flow', prompt_upgrade_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', prompt_upgrade_text)
        self.assertIn("FLOW auto_prompt_upgrade_flow", prompt_upgrade_text)
        self.assertNotIn('ROUTE choose_prompt_upgrade', prompt_upgrade_text)
        self.assertNotIn("ROUTE prepare_prompt_upgrade_decision", prompt_upgrade_text)
        self.assertIn("RUN_WORKFLOW prompt_upgrade", prompt_upgrade_text)
        self.assertIn('WORKFLOW "workflows/wf-prompt-upgrade/wf/workflow.lgwf"', prompt_upgrade_text)

        e2e_text = (PACKAGE_ROOT / "wf/04_e2e_generate/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE e2e_generate_auto_route", e2e_text)
        self.assertIn("ROUTE e2e_generate_auto_route", e2e_text)
        self.assertIn("WHEN true THEN auto_e2e_generate_flow", e2e_text)
        self.assertNotIn("WHEN true THEN run_e2e_generate_flow", e2e_text)
        self.assertIn("CHOICE choose_e2e_generate", e2e_text)
        self.assertNotIn("ROUTES {", e2e_text)
        self.assertIn('OPTION run LABEL "生成 E2E 测试" THEN run_e2e_generate_flow', e2e_text)
        self.assertIn('OPTION auto LABEL "开启自动并生成 E2E 测试" THEN auto_e2e_generate_flow', e2e_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', e2e_text)
        self.assertIn("FLOW auto_e2e_generate_flow", e2e_text)
        self.assertNotIn('ROUTE choose_e2e_generate', e2e_text)
        self.assertNotIn("ROUTE prepare_e2e_generate_decision", e2e_text)
        self.assertIn("RUN_WORKFLOW e2e_generate", e2e_text)
        self.assertIn('WORKFLOW "workflows/e2e-test-generator/workflow.lgwf"', e2e_text)
        self.assertIn('WRITE workspace file ".lgwf/post_fix_generated_tests.materialized.json"', e2e_text)

        script_flow_text = (PACKAGE_ROOT / "wf/05_run_generated_tests/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE script_flow_e2e_auto_route", script_flow_text)
        self.assertIn("ROUTE script_flow_e2e_auto_route", script_flow_text)
        self.assertIn("WHEN true THEN auto_script_flow_e2e_flow", script_flow_text)
        self.assertNotIn("WHEN true THEN run_script_flow_e2e_flow", script_flow_text)
        self.assertNotIn("ROUTES {", script_flow_text)
        self.assertIn('OPTION skip LABEL "跳过 script_flow E2E" THEN skip_script_flow_e2e_flow', script_flow_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行 script_flow E2E" THEN auto_script_flow_e2e_flow', script_flow_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', script_flow_text)
        self.assertIn("FLOW auto_script_flow_e2e_flow", script_flow_text)

        runtime_fake_text = (PACKAGE_ROOT / "wf/06_runtime_fake_e2e/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE runtime_fake_e2e_auto_route", runtime_fake_text)
        self.assertIn("ROUTE runtime_fake_e2e_auto_route", runtime_fake_text)
        self.assertIn("WHEN true THEN auto_runtime_fake_e2e_flow", runtime_fake_text)
        self.assertNotIn("WHEN true THEN run_runtime_fake_e2e_flow", runtime_fake_text)
        self.assertNotIn("ROUTES {", runtime_fake_text)
        self.assertIn('OPTION skip LABEL "跳过 runtime_fake E2E" THEN skip_runtime_fake_e2e_flow', runtime_fake_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行 runtime_fake E2E" THEN auto_runtime_fake_e2e_flow', runtime_fake_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', runtime_fake_text)
        self.assertIn("FLOW auto_runtime_fake_e2e_flow", runtime_fake_text)

        real_positive_text = (PACKAGE_ROOT / "wf/07_real_positive_e2e/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE choose_real_positive_e2e", real_positive_text)
        self.assertNotIn("READ state.lgwf_wf_post_fix.post_fix_decisions.auto_enabled", real_positive_text)
        self.assertNotIn("ROUTES {", real_positive_text)
        self.assertIn('OPTION skip LABEL "跳过真实正向 E2E" THEN skip_real_positive_e2e_flow', real_positive_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行真实正向 E2E" THEN auto_real_positive_e2e_flow', real_positive_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', real_positive_text)
        self.assertIn("FLOW auto_real_positive_e2e_flow", real_positive_text)

        wf_fix_text = (PACKAGE_ROOT / "wf/08_wf_fix_positive_e2e/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ENTRY NODE choose_wf_fix_positive_e2e", wf_fix_text)
        self.assertNotIn("READ state.lgwf_wf_post_fix.post_fix_decisions.auto_enabled", wf_fix_text)
        self.assertNotIn("ROUTES {", wf_fix_text)
        self.assertIn('OPTION skip LABEL "跳过 wf_fix 正向 E2E" THEN skip_wf_fix_positive_e2e_flow', wf_fix_text)
        self.assertIn('OPTION auto LABEL "开启自动并运行 wf_fix 正向 E2E" THEN auto_wf_fix_positive_e2e_flow', wf_fix_text)
        self.assertIn('OPTION stop LABEL "停止整个 wf-post-fix" THEN FAIL_ALL', wf_fix_text)
        self.assertIn("FLOW auto_wf_fix_positive_e2e_flow", wf_fix_text)

    def test_audit_fix_choice_routes_compile_to_named_flow_entry_nodes(self) -> None:
        compiled = self.compile_workflow(PACKAGE_ROOT / "wf/02_audit_fix/workflow.lgwf")
        routes = {item["from"]: item["branches"] for item in compiled["routes"]}
        nodes = {item["id"]: item for item in compiled["nodes"]}

        self.assertEqual(
            {"true": "set_audit_fix_auto", "false": "choose_audit_fix"},
            routes["audit_fix_auto_route"],
        )
        self.assertEqual(
            {
                "run": "build_audit_fix_input",
                "skip": "skip_audit_fix",
                "auto": "set_audit_fix_auto",
                "stop": "FAIL_ALL",
            },
            routes["choose_audit_fix"],
        )
        self.assertIn(["build_audit_fix_input", "audit_fix"], compiled["edges"])
        self.assertIn(["audit_fix", "finish_audit_fix_stage"], compiled["edges"])
        self.assertIn(["set_audit_fix_auto", "build_audit_fix_input"], compiled["edges"])
        self.assertEqual(
            {
                "run": "运行 audit 修复",
                "skip": "跳过 audit 修复",
                "auto": "开启自动并运行 audit 修复",
                "stop": "停止整个 wf-post-fix",
            },
            nodes["choose_audit_fix"]["config"]["option_labels"],
        )

        build_contract = nodes["build_audit_fix_input"]["config"]["contract"]
        self.assertIn("lgwf_wf_post_fix.audit_fix_input", build_contract["writes_state"])
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_target.json", "type": "file"},
            build_contract["reads_resources"],
        )

        skip_contract = nodes["skip_audit_fix"]["config"]["contract"]
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_decisions.json", "type": "file"},
            skip_contract["writes_resources"],
        )
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_stage_results.json", "type": "file"},
            skip_contract["writes_resources"],
        )

        child_contract = nodes["audit_fix"]["config"]["contract"]
        self.assertEqual(["lgwf_wf_post_fix.audit_fix_input"], child_contract["reads_state"])
        self.assertEqual("lgwf_wf_post_fix.audit_fix_result", nodes["audit_fix"]["config"]["result_path"])

    def test_audit_fix_stage_declares_local_artifact_boundaries(self) -> None:
        contract = json.loads((PACKAGE_ROOT / "wf/02_audit_fix/artifact_contracts.json").read_text(encoding="utf-8"))

        self.assertIn(".lgwf/post_fix_target.json", contract["bootstrap_inputs"])
        self.assertIn(".lgwf/post_fix_decisions.json", contract["bootstrap_inputs"])
        self.assertIn(".lgwf/post_fix_decisions/audit_fix.json", contract["bootstrap_inputs"])
        self.assertIn(".lgwf/post_fix_decisions.json", contract["final_outputs"])
        self.assertIn(".lgwf/post_fix_decisions/audit_fix.json", contract["final_outputs"])
        self.assertIn(".lgwf/post_fix_stage_results.json", contract["final_outputs"])

    def test_prompt_fix_choice_routes_compile_to_named_flow_entry_nodes(self) -> None:
        compiled = self.compile_workflow(PACKAGE_ROOT / "wf/02_prompt_fix/workflow.lgwf")
        routes = {item["from"]: item["branches"] for item in compiled["routes"]}
        nodes = {item["id"]: item for item in compiled["nodes"]}

        self.assertEqual(
            {"true": "set_prompt_fix_auto", "false": "choose_prompt_fix"},
            routes["prompt_fix_auto_route"],
        )
        self.assertEqual(
            {
                "run": "build_prompt_fix_input",
                "skip": "skip_prompt_fix",
                "auto": "set_prompt_fix_auto",
                "stop": "FAIL_ALL",
            },
            routes["choose_prompt_fix"],
        )
        self.assertIn(["build_prompt_fix_input", "prompt_fix"], compiled["edges"])
        self.assertIn(["prompt_fix", "finish_prompt_fix_stage"], compiled["edges"])
        self.assertIn(["set_prompt_fix_auto", "build_prompt_fix_input"], compiled["edges"])
        self.assertEqual(
            {
                "run": "运行 prompt 修复",
                "skip": "跳过 prompt 修复",
                "auto": "开启自动并运行 prompt 修复",
                "stop": "停止整个 wf-post-fix",
            },
            nodes["choose_prompt_fix"]["config"]["option_labels"],
        )

        build_contract = nodes["build_prompt_fix_input"]["config"]["contract"]
        self.assertIn("lgwf_wf_post_fix.prompt_fix_input", build_contract["writes_state"])
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_target.json", "type": "file"},
            build_contract["reads_resources"],
        )

        child_contract = nodes["prompt_fix"]["config"]["contract"]
        self.assertEqual(["lgwf_wf_post_fix.prompt_fix_input"], child_contract["reads_state"])
        self.assertEqual("lgwf_wf_post_fix.prompt_fix_result", nodes["prompt_fix"]["config"]["result_path"])

    def test_prepare_and_finish_contracts_compile_to_node_configs(self) -> None:
        prepare = self.compile_workflow(PACKAGE_ROOT / "wf/01_prepare_target/workflow.lgwf")
        prepare_nodes = {item["id"]: item for item in prepare["nodes"]}
        collect_contract = prepare_nodes["collect_post_fix_target"]["config"]["contract"]
        normalize_contract = prepare_nodes["normalize_post_fix_target"]["config"]["contract"]

        self.assertIn("post_fix_target", collect_contract["reads_state"])
        self.assertIn("lgwf_wf_post_fix.post_fix_target_request", collect_contract["writes_state"])
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_target.request.json", "type": "file"},
            collect_contract["writes_resources"],
        )
        self.assertIn("lgwf_wf_post_fix.post_fix_target", normalize_contract["writes_state"])
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_decisions.json", "type": "file"},
            normalize_contract["writes_resources"],
        )

        finish = self.compile_workflow(PACKAGE_ROOT / "wf/09_finish/workflow.lgwf")
        summarize_contract = finish["nodes"][0]["config"]["contract"]
        self.assertIn(
            {"root": "workspace", "path": ".lgwf/post_fix_stage_results.json", "type": "file"},
            summarize_contract["reads_resources"],
        )
        self.assertIn(
            {"root": "workspace", "path": "reports/wf-post-fix/report.md", "type": "file"},
            summarize_contract["writes_resources"],
        )

    def test_root_workflow_only_sequences_stage_steps(self) -> None:
        compiled = self.compile_workflow(PACKAGE_ROOT / "wf/workflow.lgwf")

        self.assertEqual("prepare_target", compiled["entry_point"])
        self.assertEqual([], compiled["routes"])
        self.assertEqual(
            [
                ["prepare_target", "audit_fix_stage"],
                ["audit_fix_stage", "prompt_fix_stage"],
                ["prompt_fix_stage", "prompt_upgrade_stage"],
                ["prompt_upgrade_stage", "e2e_generate_stage"],
                ["e2e_generate_stage", "route_script_flow_e2e"],
                ["route_script_flow_e2e", "route_runtime_fake_e2e"],
                ["route_runtime_fake_e2e", "route_real_positive"],
                ["route_real_positive", "route_wf_fix_positive"],
                ["route_wf_fix_positive", "finish"],
            ],
            compiled["edges"],
        )


class TargetNormalizationTests(unittest.TestCase):
    def test_normalize_target_defaults_package_root_dirs_and_manual_mode(self) -> None:
        module = load_module("wf/01_prepare_target/scripts/normalize_post_fix_target.py", "normalize_post_fix_target")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = root / "wf" / "workflow.lgwf"
            workflow.parent.mkdir()
            workflow.write_text("WORKFLOW sample;", encoding="utf-8")

            target = module.normalize_target({"target_workflow_lgwf": str(workflow)})

        self.assertEqual(str(workflow), target["target_workflow_lgwf"])
        self.assertEqual(str(workflow.parent), target["target_package_root"])
        self.assertEqual([str(workflow.parent)], target["target_dirs"])
        self.assertEqual("manual", target["mode"])

    def test_normalize_target_rejects_unknown_mode(self) -> None:
        module = load_module("wf/01_prepare_target/scripts/normalize_post_fix_target.py", "normalize_post_fix_target")

        with self.assertRaises(ValueError):
            module.normalize_target({"target_workflow_lgwf": "D:/demo/workflow.lgwf", "mode": "auto_all"})


class StageDecisionTests(unittest.TestCase):
    def test_auto_runs_allowed_stage_without_approval(self) -> None:
        module = load_module("wf/shared/scripts/post_fix_common.py", "post_fix_common")

        decision = module.resolve_stage_decision(
            stage_id="audit_fix",
            target={"mode": "manual"},
            decisions={"auto_enabled": True, "stages": []},
        )

        self.assertEqual("run", decision["route"])
        self.assertEqual("auto", decision["source"])
        self.assertFalse(decision["requires_approval"])

    def test_auto_still_requires_real_positive_approval(self) -> None:
        module = load_module("wf/shared/scripts/post_fix_common.py", "post_fix_common")

        decision = module.resolve_stage_decision(
            stage_id="real_positive_e2e",
            target={"mode": "manual"},
            decisions={"auto_enabled": True, "stages": []},
        )

        self.assertEqual("ask", decision["route"])
        self.assertTrue(decision["requires_approval"])

    def test_parse_stage_response_accepts_auto(self) -> None:
        module = load_module("wf/shared/scripts/post_fix_common.py", "post_fix_common")

        parsed = module.parse_stage_response({"decision": "auto", "reason": "后续自动跑"})

        self.assertEqual("auto", parsed["decision"])
        self.assertEqual("后续自动跑", parsed["reason"])

    def test_enable_auto_for_stage_writes_stage_decision_file(self) -> None:
        module = load_module("wf/shared/scripts/post_fix_common.py", "post_fix_common_auto_file")

        current = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                decision = module.enable_auto_for_stage("prompt_upgrade")
            finally:
                os.chdir(current)

            stage_decision = json.loads(
                (Path(tmp) / ".lgwf/post_fix_decisions/prompt_upgrade.json").read_text(encoding="utf-8")
            )
            decisions = json.loads((Path(tmp) / ".lgwf/post_fix_decisions.json").read_text(encoding="utf-8"))

        self.assertEqual({"decision": "auto", "reason": "用户选择 auto"}, stage_decision)
        self.assertEqual("prompt_upgrade", decision["stage_id"])
        self.assertEqual("run", decision["route"])
        self.assertEqual("auto", decision["source"])
        self.assertEqual([decision], decisions["stages"])


class MapperTests(unittest.TestCase):
    def test_audit_fix_input_matches_child_contract_and_scans_wf_dir(self) -> None:
        module = load_module("wf/02_audit_fix/scripts/build_audit_fix_input.py", "build_audit_fix_input")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wf_dir = root / "wf"
            wf_dir.mkdir()
            workflow_lgwf = wf_dir / "workflow.lgwf"
            workflow_lgwf.write_text("WORKFLOW demo;\n", encoding="utf-8")

            payload = module.build_audit_fix_input(
                {
                    "target_workflow_lgwf": str(workflow_lgwf),
                    "target_package_root": str(root),
                    "target_dirs": [str(root)],
                }
            )

        self.assertEqual(
            {
                "audit_fix_target": {
                    "target_paths": [str(wf_dir)],
                    "allowed_dirs": [str(root)],
                    "mode": "apply",
                    "scope_mode": "explicit",
                    "max_targets": 32,
                }
            },
            payload,
        )

    def test_prompt_fix_input_matches_child_contract(self) -> None:
        module = load_module("wf/02_prompt_fix/scripts/build_prompt_fix_input.py", "build_prompt_fix_input")

        payload = module.build_prompt_fix_input(
            {
                "target_workflow_lgwf": "D:/demo/wf/workflow.lgwf",
                "target_package_root": "D:/demo/wf",
                "target_dirs": ["D:/demo/wf"],
            }
        )

        self.assertEqual(
            {
                "prompt_fix_target": {
                    "target_workflow_lgwf": "D:/demo/wf/workflow.lgwf",
                    "target_package_root": "D:/demo/wf",
                    "target_dirs": ["D:/demo/wf"],
                }
            },
            payload,
        )

    def test_prompt_upgrade_input_matches_child_contract(self) -> None:
        module = load_module("wf/03_prompt_upgrade/scripts/build_prompt_upgrade_input.py", "build_prompt_upgrade_input")

        payload = module.build_prompt_upgrade_input(
            {
                "target_workflow_lgwf": "D:/demo/wf/workflow.lgwf",
                "target_package_root": "D:/demo/wf",
                "target_dirs": ["D:/demo/wf"],
            }
        )

        self.assertIn("prompt_upgrade_target", payload)
        self.assertEqual("D:/demo/wf/workflow.lgwf", payload["prompt_upgrade_target"]["target_workflow_lgwf"])

    def test_e2e_input_matches_child_contract(self) -> None:
        module = load_module("wf/04_e2e_generate/scripts/build_e2e_input.py", "build_e2e_input")

        payload = module.build_e2e_input(
            {
                "target_workflow_lgwf": "D:/demo/my-flow/workflow.lgwf",
                "target_package_root": "D:/demo/my-flow",
            }
        )

        self.assertEqual("D:/demo/my-flow/workflow.lgwf", payload["workflow_lgwf"])
        self.assertEqual("D:/demo/my-flow", payload["workflow_root"])
        self.assertEqual("tests", payload["test_output_dir"])
        self.assertEqual(["script_flow", "runtime_fake"], payload["test_types"])


if __name__ == "__main__":
    unittest.main()
