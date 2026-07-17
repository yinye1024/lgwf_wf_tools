import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def load_module(relative_path: str, module_name: str):
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IndexPromptFilesTests(unittest.TestCase):
    def test_build_inventory_skips_runtime_and_cache_dirs(self):
        module = load_module(
            "wf/04_confirm_business_flow/scripts/index_prompt_files.py",
            "index_prompt_files",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "flow" / "agents").mkdir(parents=True)
            (root / "flow" / "workflow.lgwf").write_text("WORKFLOW demo;", encoding="utf-8")
            (root / ".lgwf" / "cache").mkdir(parents=True)
            (root / "__pycache__").mkdir()
            inventory = module.build_inventory(root)
        files = [item["path"] for item in inventory["files"]]
        self.assertEqual(files, ["flow/workflow.lgwf"])
        self.assertEqual(inventory["workflow_files"], ["flow/workflow.lgwf"])


class PreparePayloadTests(unittest.TestCase):
    def test_build_payload_rejects_invalid_relative_paths(self):
        module = load_module(
            "wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py",
            "prepare_wf_create_fast_payload",
        )
        with self.assertRaises(ValueError):
            module.normalize_package_path("../outside", "target_package_root")

    def test_build_payload_uses_confirmed_input(self):
        module = load_module(
            "wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py",
            "prepare_wf_create_fast_payload",
        )
        source_business_contract = {
            "goal": "审批路由",
            "decision_rules": [{"rule_id": "auto-low", "description": "低金额低风险自动通过"}],
        }
        conversion_mapping = [
            {
                "source_item": "flow/agents/classify_risk.md",
                "target_lgwf_design": "classify_risk step",
                "mapping_type": "preserve_business_logic",
            }
        ]
        payload = module.build_payload(
            confirmed_input={
                "workflow_name": "wf-convert",
                "target_package_root": "C:/Users/Administrator/Desktop/tmp3/lgwf_wf",
                "source_root": "samples/source-flow",
                "report_fields": ["summary"],
                "source_business_contract": source_business_contract,
                "conversion_mapping": conversion_mapping,
                "parity_requirements": [{"requirement_id": "audit", "description": "必须保留审计摘要"}],
                "discarded_prompt_techniques": [{"technique": "prefill", "reason": "prompt 执行技巧"}],
            },
            package_profile="internal_workflow_package",
        )
        self.assertEqual(payload["workflow_name"], "wf-convert")
        self.assertEqual(payload["target_package_root"], "C:\\Users\\Administrator\\Desktop\\tmp3\\lgwf_wf")
        self.assertNotIn("source_root", payload)
        self.assertNotIn("request", payload)
        self.assertEqual(payload["package_profile"], "internal_workflow_package")
        self.assertEqual(payload["source_business_contract"], source_business_contract)
        self.assertEqual(payload["conversion_mapping"], conversion_mapping)
        self.assertEqual(payload["prompt_workflow_context"]["parity_requirements"][0]["requirement_id"], "audit")
        self.assertEqual(payload["prompt_workflow_context"]["discarded_prompt_techniques"][0]["technique"], "prefill")

    def test_build_wf_create_fast_target_preserves_raw_intent_and_structured_context(self):
        module = load_module(
            "wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py",
            "prepare_wf_create_fast_payload_structured",
        )
        payload = module.build_payload(
            confirmed_input={
                "workflow_name": "wf-convert",
                "target_package_root": "skills/lgwf-wf-tools/workflows/wf-convert",
                "raw_intent": "创建审批路由 workflow",
                "source_business_contract": {"goal": "审批路由"},
                "conversion_mapping": [{"mapping_type": "preserve_business_logic"}],
            },
        )
        target = module.build_wf_create_fast_target(payload)
        self.assertEqual(target["raw_intent"], "创建审批路由 workflow")
        self.assertEqual(target["source_business_contract"], {"goal": "审批路由"})
        self.assertEqual(target["conversion_mapping"], [{"mapping_type": "preserve_business_logic"}])

        minimal_target = module.build_wf_create_fast_target({"raw_intent": "minimal intent"})
        self.assertEqual(minimal_target, {"input_mode": "converted_contract", "raw_intent": "minimal intent"})

    def test_launch_input_passes_handoff_as_target_file(self):
        module = load_module(
            "wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py",
            "prepare_wf_create_fast_payload_request_context",
        )
        payload = module.build_payload(
            confirmed_input={
                "workflow_name": "wf-convert",
                "target_package_root": "skills/lgwf-wf-tools/workflows/generated",
                "source_root": "skills/source-prompt-workflow",
                "raw_intent": "把 prompt workflow 转成 LGWF workflow",
                "request": {"target_file": "skills/source-prompt-workflow/README.md"},
            },
        )

        target = module.build_wf_create_fast_target(payload)
        launch_input = module.build_wf_create_fast_launch_input(".lgwf/wf_create_fast_handoff.json")
        handoff = module.build_handoff_state(
            target_file=".lgwf/wf_create_fast_handoff.json",
            target_file_for_launch="D:/tmp/.lgwf/wf_create_fast_handoff.json",
            launch_input_file="D:/tmp/.lgwf/wf_create_fast_launch_input.json",
        )

        self.assertNotIn("source_root", target)
        self.assertNotIn("request", target)
        self.assertEqual(launch_input["request"]["target_file"], ".lgwf/wf_create_fast_handoff.json")
        self.assertEqual(handoff["next_action"], "start_workflow")
        self.assertEqual(handoff["input_json_file"], "D:/tmp/.lgwf/wf_create_fast_launch_input.json")
        self.assertIn("wf_create_fast_launch_input.json", handoff["suggested_command"])
        self.assertTrue(handoff["requires_user_confirmation"])
        self.assertFalse(handoff["auto_execute_downstream_workflow"])


class SelfImproveContractTests(unittest.TestCase):
    def test_wf_convert_has_self_contained_self_improve_structure(self):
        expected_files = [
            "self-improve/AGENTS.md",
            "self-improve/README.md",
            "self-improve/manifest.json",
            "self-improve/scripts/self_improve.py",
            "self-improve/scripts/run_trace_eval.py",
            "self-improve/scripts/check_self_improve.py",
            "self-improve/evals/baseline-cases.json",
            "self-improve/templates/proposal.template.md",
            "self-improve/trace-eval/workflow.json",
            "self-improve/trace-eval/golden_cases/runtime_trace_contract/spec.json",
        ]
        for relative_path in expected_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((PACKAGE_ROOT / relative_path).is_file(), relative_path)

        manifest = json.loads((PACKAGE_ROOT / "self-improve/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("wf-convert-self-improve", manifest["name"])
        self.assertEqual(2, manifest["version"])
        self.assertEqual(".local/self-improve", manifest["local_state_root"])
        self.assertIn("trace-eval", manifest["commands"])
        self.assertIn("check", manifest["commands"])


class RunWorkflowTests(unittest.TestCase):
    def test_convert_prompts_require_business_contract_and_prompt_technique_separation(self):
        prompt_paths = {
            PACKAGE_ROOT / "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/spec.md": [
                "source_business_contract",
                "prompt_execution_mechanics",
                "discarded_prompt_techniques",
            ],
            PACKAGE_ROOT / "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/observe.md": [
                "source_business_contract",
                "prompt_execution_mechanics",
                "discarded_prompt_techniques",
                "conversion_mapping",
                "parity_requirements",
            ],
            PACKAGE_ROOT / "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": [
                "source_business_contract",
                "prompt_execution_mechanics",
                "discarded_prompt_techniques",
                "conversion_mapping",
                "parity_requirements",
            ],
            PACKAGE_ROOT / "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": [
                "source_business_contract",
                "prompt_execution_mechanics",
                "conversion_mapping",
                "parity_requirements",
            ],
            PACKAGE_ROOT / "wf/04_confirm_business_flow/confirm_create_input.md": [
                "source_business_contract",
                "prompt_execution_mechanics",
                "discarded_prompt_techniques",
                "conversion_mapping",
                "parity_requirements",
            ],
        }
        for path, required_terms in prompt_paths.items():
            text = path.read_text(encoding="utf-8")
            for term in required_terms:
                with self.subTest(path=path.name, term=term):
                    self.assertIn(term, text)

    def test_react_uses_composite_observe_and_thin_decide_contracts(self):
        workflow_text = (
            PACKAGE_ROOT / "wf/04_confirm_business_flow/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertIn("OBSERVE WORKFLOW inspection_quality_gate", workflow_text)
        self.assertIn("OBSERVE WORKFLOW create_input_quality_gate", workflow_text)
        for expected_ref in (
            'SPEC "inspect_prompt_workflow_react/agents/spec.md"',
            'PROMPT "inspect_prompt_workflow_react/agents/reason.md"',
            'PROMPT "inspect_prompt_workflow_react/agents/act.md"',
            'WORKFLOW "inspect_prompt_workflow_react/ob.lgwf"',
            'SPEC "propose_create_input_react/agents/spec.md"',
            'PROMPT "propose_create_input_react/agents/reason.md"',
            'PROMPT "propose_create_input_react/agents/act.md"',
            'WORKFLOW "propose_create_input_react/ob.lgwf"',
        ):
            with self.subTest(expected_ref=expected_ref):
                self.assertIn(expected_ref, workflow_text)
        self.assertNotIn('SPEC "agents/', workflow_text)
        self.assertNotIn('PROMPT "agents/', workflow_text)

        inspection_decide_contract = workflow_text.split(
            'SCRIPT "inspect_prompt_workflow_react/scripts/decide.py"', 1
        )[1].split("};", 1)[0]
        self.assertIn('READ workspace file ".lgwf/prompt_workflow_inspection_observe.json"', inspection_decide_contract)
        self.assertNotIn('READ workspace file ".lgwf/prompt_workflow_inspection.json"', inspection_decide_contract)

        proposal_decide_contract = workflow_text.split(
            'SCRIPT "propose_create_input_react/scripts/decide.py"', 1
        )[1].split("};", 1)[0]
        self.assertIn('READ workspace file ".lgwf/wf_create_fast_input_observe.json"', proposal_decide_contract)
        self.assertNotIn('READ workspace file ".lgwf/wf_create_fast_input_proposal.json"', proposal_decide_contract)

    def test_semantic_observe_prompts_delegate_deterministic_checks_to_python(self):
        for relative_path in (
            "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/observe.md",
            "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md",
        ):
            text = (PACKAGE_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("Python Observe 已负责", text)
            self.assertIn("不要重复检查", text)
            self.assertIn("不要输出顶层 `verdict`", text)

    def test_workflow_handoffs_wf_create_fast_to_main_agent(self):
        workflow_text = (PACKAGE_ROOT / "wf/workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("RUN_WORKFLOW wf_create_fast", workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_fast_handoff_payload", workflow_text)
        self.assertIn("WRITE workspace file \".lgwf/wf_create_fast_handoff.json\"", workflow_text)
        self.assertIn("HANDOFF handoff_to_wf_create_fast", workflow_text)
        self.assertIn('PROMPT "handoff_wf_create_fast.md"', workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_fast_handoff", workflow_text)
        self.assertNotIn("INPUT state.lgwf_wf_convert.wf_create_fast_payload.wf_create_fast_payload", workflow_text)
        self.assertNotIn("finish_wf_create_fast_run", workflow_text)
        self.assertNotIn("capture_wf_create_fast_result", workflow_text)
        self.assertNotIn("verify_business_parity", workflow_text)
        self.assertNotIn("summarize_result", workflow_text)
        self.assertNotIn("prepare_main_agent_authoring_handoff", workflow_text)
        self.assertNotIn("handoff_main_agent_authoring", workflow_text)
        self.assertNotIn('WORKFLOW "workflows/wf-create/wf/workflow.lgwf"', workflow_text)
        self.assertNotIn('WORK_DIR "workflows/wf-create/ws"', workflow_text)
        self.assertNotIn("PY prepare_post_fix_handoff", workflow_text)
        self.assertNotIn("HANDOFF handoff_wf_post_fix", workflow_text)
        self.assertNotIn("SCRIPT \"10_handoff_wf_create_fast/scripts/handoff_wf_create_fast.py\"", workflow_text)
        self.assertIn(
            "THEN prepare_payload\n  THEN handoff_to_wf_create_fast;",
            workflow_text,
        )


if __name__ == "__main__":
    unittest.main()
