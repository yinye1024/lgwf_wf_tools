from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROOT = PACKAGE_ROOT / "wf"
ROOT_WORKFLOW = ROOT / "workflow.lgwf"
SUMMARY_SCRIPT = ROOT / "06_summarize_create_result" / "scripts" / "summarize_create_result.py"
STRUCTURE_VALIDATOR_SCRIPT = PACKAGE_ROOT / "scripts" / "validate_two_layer_workflow.py"
sys.dont_write_bytecode = True


def load_summary_module():
    spec = importlib.util.spec_from_file_location("lgwf_wf_create_summary", SUMMARY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class WorkflowCreateStructuredContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary_module = load_summary_module()

    def test_audit_workflow_structure_and_relative_paths(self) -> None:
        text = ROOT_WORKFLOW.read_text(encoding="utf-8")
        expected_stage_files = (
            'WORKFLOW "01_confirm_requirements/workflow.lgwf"',
            'WORKFLOW "02_confirm_business_flow/workflow.lgwf"',
            'WORKFLOW "03_confirm_step_designs/workflow.lgwf"',
            'WORKFLOW "04_implement_steps_react/workflow.lgwf"',
            'WORKFLOW "06_summarize_create_result/workflow.lgwf"',
        )
        for fragment in expected_stage_files:
            self.assertIn(fragment, text)

        self.assertNotIn("..", text)
        self.assertIsNone(re.search(r"[A-Za-z]:[\\/]", text))
        self.assertIsNone(re.search(r"\b(?:https?|file)://", text))

    def test_uses_isolated_wf_and_ws_layout(self) -> None:
        self.assertTrue(ROOT_WORKFLOW.is_file())
        self.assertFalse((PACKAGE_ROOT / "workflow.lgwf").exists())
        self.assertFalse((PACKAGE_ROOT / "SKILL.md").exists())
        self.assertTrue((PACKAGE_ROOT / "AGENTS.md").is_file())
        self.assertTrue((PACKAGE_ROOT / "ws").is_dir())
        self.assertFalse((ROOT / "ws").exists())
        self.assertFalse((ROOT / "tests").exists())

    def test_two_layer_structure_validator_exists(self) -> None:
        module = load_module(STRUCTURE_VALIDATOR_SCRIPT, "validate_two_layer_workflow")
        errors = module.validate_scaffold_paths(["wf/demo/workflow.lgwf", "wf/demo/scripts/run.py"])
        self.assertEqual(errors, [])
        self.assertTrue(module.validate_scaffold_paths(["wf/demo/sub/workflow.lgwf"]))
        self.assertTrue(module.validate_scaffold_paths(["wf/tests/test_demo.py"]))

    def test_required_files_and_dirs_exist(self) -> None:
        for relative in (
            "README.md",
            "AGENTS.md",
            "tests/README.md",
            "tests/test_scaffold_package_rules.py",
            "wf/workflow.lgwf",
            "wf/04_implement_steps_react/workflow.lgwf",
            "wf/06_summarize_create_result/workflow.lgwf",
            "wf/06_summarize_create_result/scripts/summarize_create_result.py",
        ):
            self.assertTrue((PACKAGE_ROOT / relative).exists(), relative)

        for relative in ("ws", "tests", "wf/docs/steps", "wf/02_confirm_business_flow/scripts"):
            self.assertTrue((PACKAGE_ROOT / relative).is_dir(), relative)

    def test_work_dir_boundary_is_documented_and_package_root_is_clean(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "tests" / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            )
        )
        self.assertIn("ws/.lgwf", combined)
        self.assertIn("不向目标 package 根目录写入 `.lgwf`", combined)
        self.assertFalse((PACKAGE_ROOT / ".lgwf").exists())

    def test_summary_interface_defines_future_runtime_contract(self) -> None:
        summary = self.summary_module.build_summary({})
        self.assertEqual(summary["result_kind"], "workflow_package_draft_summary")
        self.assertEqual(summary["status"], "draft_structure_ready")
        self.assertIn("python -m unittest discover tests", summary["validation"]["minimal_command"])
        self.assertIn("workflow 结构性 audit", summary["validation"]["checks"])
        self.assertIn("lgwf-wf-prompt-fix 集成", summary["scope_boundary"]["out_of_scope"])
        self.assertIn("生成出的目标 workflow 自动接入 facade 路由", summary["scope_boundary"]["out_of_scope"])

    def test_gate_workflows_own_approval_nodes_and_reject_fail_all_routes(self) -> None:
        main_workflow = ROOT_WORKFLOW.read_text(encoding="utf-8")
        for gate, workflow_ref, next_stage in (
            ("define_requirements", "01_confirm_requirements/workflow.lgwf", "design_structure"),
            ("design_structure", "02_confirm_business_flow/workflow.lgwf", "implement_draft"),
        ):
            self.assertIn(f"STEP {gate}", main_workflow)
            self.assertIn(f'WORKFLOW "{workflow_ref}"', main_workflow)
            self.assertIn("FLOW define_requirements", main_workflow)
            self.assertIn(f"THEN {next_stage}", main_workflow)
        self.assertNotIn('WHEN "approve" THEN design_structure', main_workflow)
        self.assertNotIn('WHEN "reject" THEN summarize_create_result', main_workflow)
        self.assertIn('STEP implement_draft', main_workflow)
        self.assertIn('WORKFLOW "03_confirm_step_designs/workflow.lgwf"', main_workflow)
        self.assertIn('STEP implement_steps_react', main_workflow)
        self.assertIn('WORKFLOW "04_implement_steps_react/workflow.lgwf"', main_workflow)
        self.assertIn("THEN implement_draft", main_workflow)
        self.assertIn("THEN implement_steps_react", main_workflow)
        self.assertIn("THEN summarize_create_result", main_workflow)

        child_workflows = "\n".join(
            (
                (ROOT / "01_confirm_requirements/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "02_confirm_business_flow/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8"),
            )
        )
        for node, apply_node in (
            (
                "confirm_requirements",
                "apply_confirmed_requirements",
            ),
            (
                "confirm_business_flow",
                "apply_confirmed_business_flow",
            ),
            (
                "confirm_step_designs",
                "apply_confirmed_step_designs",
            ),
        ):
            self.assertIn(f"REVIEW {node}", child_workflows)
            self.assertIn('OPTIONS ["approve", "revise", "reject"]', child_workflows)
            self.assertIn("FLOW {", child_workflows)
            self.assertIn(node, child_workflows)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', child_workflows)
            self.assertIn(f'WHEN "revise" THEN {node}', child_workflows)
            self.assertIn('WHEN "reject" THEN FAIL_ALL', child_workflows)
        for persisted in (
            ".lgwf/create_requirements_approval.json",
            ".lgwf/business_flow_approval.json",
            ".lgwf/step_design_confirmation_record.json",
        ):
            self.assertIn(f'PERSIST "{persisted}"', child_workflows)

    def test_codex_nodes_and_prompts_define_output_json_contracts(self) -> None:
        contracts = (
            (
                "01_confirm_requirements/workflow.lgwf",
                "01_confirm_requirements/agents/propose_requirements_react.md",
                ".lgwf/create_requirements_proposal.json",
                True,
            ),
            (
                "02_confirm_business_flow/workflow.lgwf",
                "02_confirm_business_flow/agents/propose_business_flow_react.md",
                ".lgwf/business_flow_proposal.json",
                True,
            ),
            (
                "03_confirm_step_designs/workflow.lgwf",
                "03_confirm_step_designs/agents/design_steps_react.md",
                ".lgwf/step_designs_proposal.json",
                True,
            ),
            (
                "04_implement_steps_react/workflow.lgwf",
                "04_implement_steps_react/agents/act.md",
                ".lgwf/implementation_result.json",
                False,
            ),
        )
        for workflow_relative, prompt_relative, artifact, uses_as_file in contracts:
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            prompt = (ROOT / prompt_relative).read_text(encoding="utf-8")
            self.assertIn(f'OUTPUT_JSON "{artifact}"', workflow)
            self.assertIn(f'WRITE workspace file "{artifact}"', workflow)
            if uses_as_file:
                self.assertIn(f'OUTPUT_JSON "{artifact}" AS_FILE', workflow)
            self.assertIn("OUTPUT_JSON", prompt)
            self.assertIn(artifact, prompt)

    def test_persisted_decision_files_have_contract_writes(self) -> None:
        expectations = (
            ("01_confirm_requirements/workflow.lgwf", ".lgwf/raw_intent_request.json"),
            ("01_confirm_requirements/workflow.lgwf", ".lgwf/create_requirements_approval.json"),
            ("02_confirm_business_flow/workflow.lgwf", ".lgwf/business_flow_approval.json"),
            ("03_confirm_step_designs/workflow.lgwf", ".lgwf/step_design_confirmation_record.json"),
        )
        for workflow_relative, artifact in expectations:
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            self.assertIn(f'PERSIST "{artifact}"', workflow)
            self.assertIn(f'WRITE workspace file "{artifact}"', workflow)

    def test_implementation_is_react_child_workflow_with_deterministic_audit_observe(self) -> None:
        design_workflow = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        implement_workflow_path = ROOT / "04_implement_steps_react/workflow.lgwf"
        self.assertTrue(implement_workflow_path.is_file())
        implement_workflow = implement_workflow_path.read_text(encoding="utf-8")

        self.assertNotIn("CODEX implement_steps_react", design_workflow)
        self.assertIn("PY prepare_implementation_context", design_workflow)
        self.assertNotIn("PY pre_implementation_audit_check", implement_workflow)
        self.assertNotIn("THEN pre_implementation_audit_check", implement_workflow)
        self.assertIn("REACT implement_steps_react MAX 3", implement_workflow)
        self.assertIn("REASON CODEX", implement_workflow)
        self.assertIn("ACT CODEX", implement_workflow)
        self.assertIn("OBSERVE WORKFLOW observe_audit", implement_workflow)
        self.assertIn('WORKFLOW "observe_audit.lgwf"', implement_workflow)
        self.assertIn("DECIDE PY", implement_workflow)
        self.assertIn('SCRIPT "scripts/decide_implementation.py"', implement_workflow)
        self.assertIn('OUTPUT_JSON ".lgwf/implementation_result.json"', implement_workflow)
        observe_workflow = (ROOT / "04_implement_steps_react/observe_audit.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY audit_created_package", observe_workflow)
        self.assertIn('SCRIPT "scripts/audit_created_package.py"', observe_workflow)
        self.assertIn("CODEX observe_implementation", observe_workflow)
        self.assertIn('PROMPT "agents/observe.md"', observe_workflow)
        self.assertNotIn("INSTRUCTION state.lgwf_wf_create.implementation_audit_result", observe_workflow)
        self.assertIn('workspace file ".lgwf/implementation_audit_result.json"', observe_workflow)
        self.assertIn('OUTPUT_JSON ".lgwf/implementation_observe.json" AS_FILE', observe_workflow)
        self.assertIn("FLOW audit_created_package", observe_workflow)
        self.assertIn("THEN observe_implementation", observe_workflow)
        self.assertIn("UPDATES_STATE", observe_workflow)
        observe_prompt = (ROOT / "04_implement_steps_react/agents/observe.md").read_text(encoding="utf-8")
        self.assertIn(".lgwf/implementation_audit_result.json", observe_prompt)
        self.assertIn("先读取 `.lgwf/implementation_audit_result.json`", observe_prompt)
        self.assertIn("不得把脚本 audit 的失败结果改写为通过", observe_prompt)
        audit_script = (ROOT / "04_implement_steps_react/scripts/audit_created_package.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("lgwf.py audit", audit_script)
        self.assertIn("implementation_audit_result.json", audit_script)

    def test_scaffold_template_spec_is_bound_to_template_and_react_prompts(self) -> None:
        spec_path = ROOT / "02_confirm_business_flow/resources/scaffold_template_spec.md"
        template_path = ROOT / "02_confirm_business_flow/resources/scaffold_package_template.json"
        contract_path = ROOT / "02_confirm_business_flow/resources/scaffold_result_contract.md"
        step_workflow = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        spec = spec_path.read_text(encoding="utf-8")
        template = json.loads(template_path.read_text(encoding="utf-8"))
        contract = contract_path.read_text(encoding="utf-8")

        self.assertIn("scaffold_package_template.json", spec)
        self.assertIn("scaffold_result_contract.md", spec)
        self.assertIn("wf/workflow.lgwf", spec)
        self.assertIn("ws/.lgwf", spec)
        self.assertIn("internal_workflow_package", spec)
        self.assertIn("skill_wrapped_workflow", spec)
        self.assertEqual(template["template_id"], "workflow_packaged_skill")
        for profile in template["profiles"]:
            self.assertIn(profile, spec)
            self.assertIn(profile, contract)

        scaffold_resources = {
            "02_confirm_business_flow/resources/scaffold_template_spec.md",
            "02_confirm_business_flow/resources/scaffold_result_contract.md",
            "02_confirm_business_flow/resources/scaffold_package_template.json",
        }
        contracts = json.loads((ROOT / "artifact_contracts.json").read_text(encoding="utf-8"))
        script_writes = contracts["script_writes"]["prepare_dsl_reference_context"]
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context/scaffold"', step_workflow)
        self.assertIn(
            'CONTEXT workspace dir ".lgwf/create_reference_context/workflow-modular-development"',
            step_workflow,
        )
        for resource in scaffold_resources:
            self.assertTrue((ROOT / resource).is_file(), resource)
            filename = Path(resource).name
            self.assertIn(f".lgwf/create_reference_context/scaffold/{filename}", script_writes)
        self.assertIn(
            ".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md",
            script_writes,
        )

        for prompt_relative in (
            "03_confirm_step_designs/agents/design_steps_react.md",
            "04_implement_steps_react/agents/act.md",
        ):
            prompt = (ROOT / prompt_relative).read_text(encoding="utf-8")
            self.assertIn("02_confirm_business_flow/resources/scaffold_template_spec.md", prompt)
            self.assertIn(".lgwf/create_reference_context/scaffold", prompt)
            self.assertIn(".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md", prompt)
            self.assertIn("scaffold_plan", prompt)
            self.assertIn("package_profile", prompt)

    def test_apply_scripts_write_confirmed_artifacts_and_reject_invalid_paths(self) -> None:
        cases = (
            (
                "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
                "create_requirements_approval.json",
                "create_requirements_proposal.json",
                "create_requirements.json",
                "apply_requirements",
                {"workflow_name": "demo", "target_package_root": "skills/demo"},
            ),
            (
                "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
                "business_flow_approval.json",
                "business_flow_proposal.json",
                "business_flow.json",
                "apply_business_flow",
                {"workflow_name": "demo", "stages": []},
            ),
            (
                "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_designs_proposal.json",
                "step_designs.json",
                "apply_step_designs",
                {"step_designs": []},
            ),
        )
        for relative, approval_name, proposal_name, output_name, module_name, proposal in cases:
            module = load_module(ROOT / relative, module_name)
            with self.subTest(relative=relative):
                with self.assertRaises(ValueError):
                    module.normalize_relative_path(".lgwf/bad", "test_path")
                with self.assertRaises(ValueError):
                    module.normalize_relative_path("C:/bad", "test_path")
                self.assertEqual(module.output_artifact_name(), output_name)
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    lgwf_dir = root / ".lgwf"
                    lgwf_dir.mkdir()
                    (lgwf_dir / proposal_name).write_text(json.dumps(proposal), encoding="utf-8")
                    (lgwf_dir / approval_name).write_text(
                        '{"decision": "approve", "target_package_root": "skills/demo"}',
                        encoding="utf-8",
                    )
                    module.write_confirmed_artifact(root)
                    self.assertTrue((lgwf_dir / output_name).is_file())

    def test_summary_script_writes_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = self.summary_module.build_summary({})
            report = self.summary_module.write_report(root, summary)
            self.assertEqual(report.as_posix(), "reports/create-workflow/create_result_report.md")
            text = (root / report).read_text(encoding="utf-8")
            self.assertIn("lgwf-wf-create 结果汇总", text)
            self.assertIn("wf/workflow.lgwf", text)

    def test_summary_rejects_invalid_runtime_paths(self) -> None:
        for payload in (
            {"target_package_root": "C:/bad"},
            {"target_package_root": ".lgwf"},
            {"produced_files": ["workflow.lgwf", "../bad"]},
            {"produced_files": ["workflow.lgwf", ".lgwf/state.json"]},
        ):
            with self.assertRaises(ValueError):
                self.summary_module.build_summary(payload)

        with self.assertRaises(TypeError):
            self.summary_module.build_summary({"produced_files": "workflow.lgwf"})

    def test_utf8_and_chinese_docs_are_readable(self) -> None:
        docs = (
            PACKAGE_ROOT / "README.md",
            PACKAGE_ROOT / "AGENTS.md",
            PACKAGE_ROOT / "tests" / "README.md",
            ROOT / "06_summarize_create_result" / "scripts" / "summarize_create_result.py",
        )
        for path in docs:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\ufffd", text, path.as_posix())
            self.assertRegex(text, r"[\u4e00-\u9fff]", path.as_posix())

    def test_validation_docs_define_command_expectation_and_scope_boundary(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "tests" / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            )
        )
        for text in (
            "python -m unittest discover tests",
            "预期结果",
            "未覆盖范围",
            "lgwf-wf-prompt-fix",
            "lgwf-wf-tools",
            "自动修复",
            "端到端业务成功",
            "固定产物",
            "Approval 边界",
        ):
            self.assertIn(text, combined)

    def test_package_has_no_runtime_pollution(self) -> None:
        for cache_dir in PACKAGE_ROOT.rglob("__pycache__"):
            shutil.rmtree(cache_dir)
        forbidden = {".tmp", "__pycache__", ".lgwf"}
        for path in PACKAGE_ROOT.rglob("*"):
            if ".local" in path.relative_to(PACKAGE_ROOT).parts:
                continue
            if path == PACKAGE_ROOT / "ws" / ".lgwf":
                continue
            self.assertNotIn(path.name, forbidden, path)


if __name__ == "__main__":
    unittest.main()
