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
                "target_package_root": "skills/lgwf-wf-tools/workflows/wf-convert",
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
        self.assertEqual(payload["source_root"], "samples/source-flow")
        self.assertEqual(payload["package_profile"], "internal_workflow_package")
        self.assertEqual(payload["source_business_contract"], source_business_contract)
        self.assertEqual(payload["conversion_mapping"], conversion_mapping)
        self.assertEqual(payload["prompt_workflow_context"]["parity_requirements"][0]["requirement_id"], "audit")
        self.assertEqual(payload["prompt_workflow_context"]["discarded_prompt_techniques"][0]["technique"], "prefill")

    def test_build_wf_create_fast_input_preserves_raw_intent_and_structured_context(self):
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
        child_input = module.build_wf_create_fast_input(payload)
        self.assertEqual(child_input["raw_intent"], "创建审批路由 workflow")
        self.assertEqual(child_input["source_business_contract"], {"goal": "审批路由"})
        self.assertEqual(child_input["conversion_mapping"], [{"mapping_type": "preserve_business_logic"}])

        minimal_child_input = module.build_wf_create_fast_input({"raw_intent": "minimal intent"})
        self.assertEqual(minimal_child_input, {"raw_intent": "minimal intent"})

    def test_build_wf_create_fast_input_passes_source_root_as_creation_context_request(self):
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

        child_input = module.build_wf_create_fast_input(payload)

        self.assertEqual(child_input["request"]["target_dir"], "skills/source-prompt-workflow")
        self.assertEqual(child_input["request"]["target_file"], "skills/source-prompt-workflow/README.md")
        self.assertNotIn("target_package_root", child_input["request"])


class MapWfCreateFastInputTests(unittest.TestCase):
    def test_extract_wf_create_fast_input_accepts_nested_payload(self):
        module = load_module("wf/scripts/map_wf_create_fast_input.py", "map_wf_create_fast_input_nested")
        payload = {
            "prompt_convert_payload": {"workflow_name": "demo"},
            "wf_create_fast_payload": {
                "raw_intent": "创建 demo workflow",
                "request": {"target_dir": "skills/source-prompt-workflow"},
            },
        }

        child_input = module.extract_wf_create_fast_input(payload)

        self.assertEqual(child_input["raw_intent"], "创建 demo workflow")
        self.assertEqual(child_input["request"]["target_dir"], "skills/source-prompt-workflow")

    def test_extract_wf_create_fast_input_accepts_flat_wf_create_fast_input(self):
        module = load_module("wf/scripts/map_wf_create_fast_input.py", "map_wf_create_fast_input_flat")
        payload = {
            "raw_intent": "创建 demo workflow",
            "request": {"target_dir": "skills/source-prompt-workflow"},
        }

        self.assertEqual(module.extract_wf_create_fast_input(payload), payload)

    def test_extract_wf_create_fast_input_accepts_fast_nested_payload(self):
        module = load_module("wf/scripts/map_wf_create_fast_input.py", "map_wf_create_fast_input_fast")
        payload = {
            "prompt_convert_payload": {"workflow_name": "demo"},
            "wf_create_fast_payload": {
                "raw_intent": "创建 fast demo workflow",
                "request": {"target_dir": "skills/source-prompt-workflow"},
            },
        }

        child_input = module.extract_wf_create_fast_input(payload)

        self.assertEqual(child_input["raw_intent"], "创建 fast demo workflow")
        self.assertEqual(child_input["request"]["target_dir"], "skills/source-prompt-workflow")

    def test_extract_wf_create_fast_input_rejects_missing_raw_intent(self):
        module = load_module("wf/scripts/map_wf_create_fast_input.py", "map_wf_create_fast_input_invalid")

        with self.assertRaises(ValueError):
            module.extract_wf_create_fast_input({"wf_create_fast_payload": {"request": {"target_dir": "source"}}})


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
        prompt_paths = [
            PACKAGE_ROOT / "wf/04_confirm_business_flow/agents/inspect_prompt_workflow_react.md",
            PACKAGE_ROOT / "wf/04_confirm_business_flow/agents/inspect_observe.md",
            PACKAGE_ROOT / "wf/04_confirm_business_flow/agents/propose_act.md",
            PACKAGE_ROOT / "wf/04_confirm_business_flow/agents/propose_observe.md",
            PACKAGE_ROOT / "wf/04_confirm_business_flow/confirm_create_input.md",
        ]
        required_terms = [
            "source_business_contract",
            "prompt_execution_mechanics",
            "discarded_prompt_techniques",
            "conversion_mapping",
            "parity_requirements",
        ]
        for path in prompt_paths:
            text = path.read_text(encoding="utf-8")
            for term in required_terms:
                with self.subTest(path=path.name, term=term):
                    self.assertIn(term, text)

    def test_workflow_handoffs_wf_create_fast_to_main_agent(self):
        workflow_text = (PACKAGE_ROOT / "wf/workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("RUN_WORKFLOW wf_create_fast", workflow_text)
        self.assertIn("PY map_wf_create_fast_input", workflow_text)
        self.assertIn('SCRIPT "scripts/map_wf_create_fast_input.py"', workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_fast_input", workflow_text)
        self.assertIn("PY prepare_wf_create_fast_handoff", workflow_text)
        self.assertIn('SCRIPT "scripts/prepare_wf_create_fast_handoff.py"', workflow_text)
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
            "THEN map_wf_create_fast_input\n  THEN prepare_wf_create_fast_handoff\n  THEN handoff_to_wf_create_fast;",
            workflow_text,
        )

    def test_prepare_handoff_payload_points_main_agent_to_wf_create_fast(self):
        module = load_module("wf/scripts/prepare_wf_create_fast_handoff.py", "prepare_wf_create_fast_handoff_contract")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            child_input = {"raw_intent": "创建 demo workflow", "request": {"target_dir": "samples/demo"}}
            (lgwf_dir / "wf_create_fast_input_for_wf_create_fast.json").write_text(
                json.dumps(child_input, ensure_ascii=False),
                encoding="utf-8",
            )
            (lgwf_dir / "wf_create_fast_payload.json").write_text(
                json.dumps({"prompt_convert_payload": {"workflow_name": "demo"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            payload = module.build_handoff_payload(child_input, root)

        self.assertEqual(payload["next_action"], "start_workflow")
        self.assertEqual(payload["next_workflow_id"], "wf-create-fast")
        self.assertEqual(payload["downstream_workflow_id"], "wf-create-fast")
        self.assertTrue(
            payload["input_json_file"].replace("\\", "/").endswith("/.lgwf/wf_create_fast_input_for_wf_create_fast.json")
        )
        self.assertEqual(payload["wf_create_fast_input"]["raw_intent"], "创建 demo workflow")
        self.assertFalse(payload["auto_execute_downstream_workflow"])


if __name__ == "__main__":
    unittest.main()
