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
            "wf/07_confirm_step_designs/scripts/prepare_wf_create_payload.py",
            "prepare_wf_create_payload",
        )
        with self.assertRaises(ValueError):
            module.normalize_package_path("../outside", "target_package_root")

    def test_build_payload_uses_confirmed_input(self):
        module = load_module(
            "wf/07_confirm_step_designs/scripts/prepare_wf_create_payload.py",
            "prepare_wf_create_payload",
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

    def test_build_wf_create_input_preserves_raw_intent_compatibility_and_structured_context(self):
        module = load_module(
            "wf/07_confirm_step_designs/scripts/prepare_wf_create_payload.py",
            "prepare_wf_create_payload_structured",
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
        child_input = module.build_wf_create_input(payload)
        self.assertEqual(child_input["raw_intent"], "创建审批路由 workflow")
        self.assertEqual(child_input["source_business_contract"], {"goal": "审批路由"})
        self.assertEqual(child_input["conversion_mapping"], [{"mapping_type": "preserve_business_logic"}])

        legacy_child_input = module.build_wf_create_input({"raw_intent": "legacy intent"})
        self.assertEqual(legacy_child_input, {"raw_intent": "legacy intent"})


class SummaryTests(unittest.TestCase):
    def test_build_report_sections(self):
        module = load_module(
            "wf/09_summarize_create_result/scripts/summarize_convert_result.py",
            "summarize_convert_result",
        )
        report = module.render_report(
            {
                "workflow_name": "wf-convert",
                "analysis_summary": ["发现 1 个 workflow"],
                "approved_input_summary": ["目标包路径已确认"],
                "payload_summary": ["已生成 wf-create payload"],
                "risks": ["缺少真实样例验证"],
            }
        )
        self.assertIn("# wf-convert 转换结果汇总", report)
        self.assertIn("## 未解决风险", report)
        self.assertIn("## 业务一致性审查", report)

    def test_business_parity_report_detects_missing_rules(self):
        module = load_module(
            "wf/scripts/verify_business_parity.py",
            "verify_business_parity",
        )
        report = module.build_parity_report(
            prompt_convert_payload={
                "source_business_contract": {
                    "decision_rules": [
                        {"rule_id": "auto-low", "description": "低金额低风险自动通过"},
                        {"rule_id": "audit", "description": "所有路径保留 audit trail"},
                    ],
                    "approval_points": [{"name": "human_review"}],
                },
                "conversion_mapping": [
                    {
                        "source_business_rule": "低金额低风险自动通过",
                        "target_lgwf_design": "auto_approve route",
                        "mapping_type": "preserve_business_logic",
                    }
                ],
                "prompt_workflow_context": {
                    "discarded_prompt_techniques": [{"technique": "prefill", "reason": "不迁移"}]
                },
            },
            created_workflow={"target_package_root": "skills/generated"},
        )
        self.assertEqual(report["parity_verdict"], "revise")
        self.assertIn("audit", report["missing_business_rules"][0]["rule_id"])
        self.assertEqual(report["discarded_prompt_techniques_checked"][0]["technique"], "prefill")


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

    def test_workflow_uses_run_workflow_node_for_wf_create(self):
        workflow_text = (PACKAGE_ROOT / "wf/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("RUN_WORKFLOW wf_create", workflow_text)
        self.assertIn("PY map_wf_create_input", workflow_text)
        self.assertIn('SCRIPT "scripts/map_wf_create_input.py"', workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_input", workflow_text)
        self.assertIn('WORKFLOW "workflows/wf-create/wf/workflow.lgwf"', workflow_text)
        self.assertIn('WORK_DIR "workflows/wf-create/ws"', workflow_text)
        self.assertIn("INPUT state.lgwf_wf_convert.wf_create_input", workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_result", workflow_text)
        self.assertIn("PY capture_wf_create_result", workflow_text)
        self.assertIn('SCRIPT "scripts/capture_wf_create_result.py"', workflow_text)
        self.assertIn("INPUT state.lgwf_wf_convert.wf_create_result", workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.wf_create_result_summary", workflow_text)
        self.assertIn("PY verify_business_parity", workflow_text)
        self.assertIn('SCRIPT "scripts/verify_business_parity.py"', workflow_text)
        self.assertIn("INPUT state.lgwf_wf_convert.wf_create_result_summary", workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.business_parity_report", workflow_text)
        self.assertIn("PY prepare_post_fix_handoff", workflow_text)
        self.assertIn('SCRIPT "scripts/prepare_post_fix_handoff.py"', workflow_text)
        self.assertIn("INPUT state.lgwf_wf_convert.wf_create_result_summary", workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.post_fix_handoff_payload", workflow_text)
        self.assertIn("HANDOFF handoff_wf_post_fix", workflow_text)
        self.assertIn("CONTEXT state.lgwf_wf_convert.post_fix_handoff_payload", workflow_text)
        self.assertIn('PROMPT "handoff_wf_post_fix.md"', workflow_text)
        self.assertIn("RESULT state.lgwf_wf_convert.post_fix_handoff", workflow_text)
        self.assertNotIn("INPUT state.lgwf_wf_convert.wf_create_payload.wf_create_payload", workflow_text)
        self.assertNotIn("HANDOFF handoff_wf_create", workflow_text)
        self.assertNotIn("SCRIPT \"10_handoff_wf_create/scripts/handoff_wf_create.py\"", workflow_text)
        self.assertIn("THEN capture_wf_create_result\n  THEN verify_business_parity\n  THEN summarize_result\n  THEN prepare_post_fix_handoff\n  THEN handoff_wf_post_fix", workflow_text)

    def test_capture_summary_preserves_child_created_workflow(self):
        module = load_module("wf/scripts/capture_wf_create_result.py", "capture_wf_create_result_contract")
        child_result = {
            "status": "completed",
            "final_state": {
                "lgwf_wf_create": {
                    "summary_result": {
                        "workflow_name": "example-workflow",
                        "target_package_root": "skills/example-workflow",
                    }
                }
            },
        }
        summary = module.build_summary(child_result)
        self.assertEqual(summary["created_workflow"]["target_package_root"], "skills/example-workflow")

    def test_post_fix_handoff_payload_uses_child_created_workflow(self):
        module = load_module("wf/scripts/prepare_post_fix_handoff.py", "prepare_convert_post_fix_handoff")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = module.build_handoff_payload(
                {
                    "created_workflow": {
                        "workflow_name": "example-workflow",
                        "target_package_root": "skills/example-workflow",
                    }
                },
                root,
            )

        self.assertEqual(payload["workflow_id"], "wf-post-fix")
        self.assertEqual(
            payload["payload"]["post_fix_target"]["target_workflow_lgwf"],
            "skills/example-workflow/wf/workflow.lgwf",
        )
        self.assertEqual(payload["payload"]["post_fix_target"]["target_dirs"], ["skills/example-workflow"])

    def test_post_fix_handoff_payload_includes_parity_report(self):
        module = load_module("wf/scripts/prepare_post_fix_handoff.py", "prepare_convert_post_fix_handoff_parity")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = module.build_handoff_payload(
                {
                    "created_workflow": {
                        "workflow_name": "example-workflow",
                        "target_package_root": "skills/example-workflow",
                    },
                    "business_parity_report": {
                        "parity_verdict": "revise",
                        "report_path": ".lgwf/business_parity_report.json",
                    },
                },
                root,
            )

        self.assertEqual(payload["payload"]["business_parity_report"]["parity_verdict"], "revise")
        self.assertIn(".lgwf/business_parity_report.json", payload["source_artifacts"])


if __name__ == "__main__":
    unittest.main()
