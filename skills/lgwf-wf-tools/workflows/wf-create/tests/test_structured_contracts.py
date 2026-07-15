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
STRUCTURE_VALIDATOR_SCRIPT = PACKAGE_ROOT / "tests" / "helpers" / "validate_two_layer_workflow.py"
sys.dont_write_bytecode = True


def read_step_design_prompts() -> str:
    return "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "03_confirm_step_designs/02_step_design_proposal/agents/generate_step_designs.md",
            "03_confirm_step_designs/02_step_design_proposal/agents/reason_step_design_repair.md",
            "03_confirm_step_designs/02_step_design_proposal/agents/act_step_design_repair.md",
        )
    )


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
            'WORKFLOW "07_post_fix_handoff/workflow.lgwf"',
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

    def test_test_helper_validates_two_layer_structure(self) -> None:
        self.assertFalse((PACKAGE_ROOT / "scripts" / "validate_two_layer_workflow.py").exists())
        self.assertTrue((ROOT / "shared" / "scripts" / "validate_two_layer_workflow.py").is_file())
        module = load_module(STRUCTURE_VALIDATOR_SCRIPT, "validate_two_layer_workflow")
        errors = module.validate_scaffold_paths(["wf/demo/workflow.lgwf", "wf/demo/scripts/run.py"])
        self.assertEqual(errors, [])
        errors = module.validate_scaffold_paths(["wf/demo/sub/workflow.lgwf", "wf/demo/sub/README.md"])
        self.assertEqual(errors, [])
        self.assertTrue(module.validate_scaffold_paths(["wf/demo/sub/workflow.lgwf"]))
        self.assertTrue(module.validate_scaffold_paths(["wf/demo/sub/deeper/workflow.lgwf", "wf/demo/sub/deeper/README.md"]))
        self.assertTrue(module.validate_scaffold_paths(["wf/tests/test_demo.py"]))
        self.assertEqual(module.validate_package(PACKAGE_ROOT), [])

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
            "wf/07_post_fix_handoff/workflow.lgwf",
            "wf/07_post_fix_handoff/artifact_contracts.json",
            "wf/07_post_fix_handoff/scripts/prepare_post_fix_handoff.py",
            "wf/07_post_fix_handoff/handoff_wf_post_fix.md",
        ):
            self.assertTrue((PACKAGE_ROOT / relative).exists(), relative)

        for relative in ("ws", "tests", "wf/02_confirm_business_flow/03_scaffold_package/scripts"):
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
                (ROOT / "01_confirm_requirements/01_raw_intent/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "01_confirm_requirements/02_requirements_proposal/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "01_confirm_requirements/03_requirements_review/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "02_confirm_business_flow/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "02_confirm_business_flow/02_business_flow_review/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "02_confirm_business_flow/03_scaffold_package/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "03_confirm_step_designs/01_reference_context/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf").read_text(encoding="utf-8"),
                (ROOT / "03_confirm_step_designs/03_step_design_review/workflow.lgwf").read_text(encoding="utf-8"),
            )
        )
        for node, revision_apply, apply_node in (
            (
                "confirm_requirements",
                "prepare_requirements_revision_confirmation",
                "apply_confirmed_requirements",
            ),
            (
                "confirm_business_flow",
                "prepare_business_flow_revision_confirmation",
                "apply_confirmed_business_flow",
            ),
            (
                "confirm_step_designs",
                "prepare_step_design_revision_confirmation",
                "apply_confirmed_step_designs",
            ),
        ):
            self.assertIn(f"REVIEW {node}", child_workflows)
            self.assertIn('OPTIONS ["approve", "revise", "reject"]', child_workflows)
            self.assertIn("FLOW {", child_workflows)
            self.assertIn(node, child_workflows)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', child_workflows)
            self.assertIn(f'WHEN "revise" THEN {revision_apply}', child_workflows)
            self.assertIn(f"PY {revision_apply}", child_workflows)
            self.assertIn(f"{revision_apply}\n  THEN {node}", child_workflows)
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
                "01_confirm_requirements/02_requirements_proposal/workflow.lgwf",
                "01_confirm_requirements/02_requirements_proposal/agents/propose_requirements.md",
                ".lgwf/create_requirements_proposal.json",
                True,
            ),
            (
                "02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf",
                "02_confirm_business_flow/01_business_flow_proposal/agents/propose_business_flow.md",
                ".lgwf/business_flow_proposal.json",
                True,
            ),
            (
                "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf",
                "03_confirm_step_designs/02_step_design_proposal/agents/reason_step_design_repair.md",
                ".lgwf/step_design_repair_plan.json",
                True,
            ),
            (
                "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf",
                "04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md",
                ".lgwf/current_implementation_unit_result.json",
                True,
            ),
            (
                "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf",
                "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/agents/reason_repair.md",
                ".lgwf/implementation_repair_reason.json",
                True,
            ),
            (
                "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf",
                "04_implement_steps_react/02_repair_implementation_react/02_act_repair/agents/act_repair.md",
                ".lgwf/implementation_repair_result.json",
                True,
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

        step_design_workflow = (
            ROOT / "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf"
        ).read_text(encoding="utf-8")
        act_prompt = (
            ROOT / "03_confirm_step_designs/02_step_design_proposal/agents/act_step_design_repair.md"
        ).read_text(encoding="utf-8")
        self.assertIn('EDIT_FILE ".lgwf/step_designs_proposal.json"', step_design_workflow)
        self.assertIn('WRITE workspace file ".lgwf/step_designs_proposal.json"', step_design_workflow)
        self.assertIn("EDIT_FILE", act_prompt)
        self.assertIn(".lgwf/step_designs_proposal.json", act_prompt)
        self.assertEqual(
            2,
            step_design_workflow.count('KEEP_SESSION KEY "design_codex"'),
        )
        self.assertIn(
            'PY generate_step_designs\n  SCRIPT "scripts/generate_step_designs_proposal.py"',
            step_design_workflow,
        )
        for codex_fragment in (
            'REASON CODEX\n    PROMPT "agents/reason_step_design_repair.md"\n    KEEP_SESSION KEY "design_codex"',
            'ACT CODEX\n    PROMPT "agents/act_step_design_repair.md"\n    KEEP_SESSION KEY "design_codex"',
        ):
            self.assertIn(codex_fragment, step_design_workflow)

    def test_persisted_decision_files_have_contract_writes(self) -> None:
        expectations = (
            ("01_confirm_requirements/01_raw_intent/workflow.lgwf", ".lgwf/raw_intent_approval.json"),
            ("01_confirm_requirements/03_requirements_review/workflow.lgwf", ".lgwf/create_requirements_approval.json"),
            ("02_confirm_business_flow/02_business_flow_review/workflow.lgwf", ".lgwf/business_flow_approval.json"),
            ("03_confirm_step_designs/03_step_design_review/workflow.lgwf", ".lgwf/step_design_confirmation_record.json"),
        )
        for workflow_relative, artifact in expectations:
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            self.assertIn(f'PERSIST "{artifact}"', workflow)
            self.assertIn(f'WRITE workspace file "{artifact}"', workflow)

    def test_implementation_runs_initial_units_then_repair_react_with_internal_audit_observe(self) -> None:
        design_workflow = (ROOT / "03_confirm_step_designs/03_step_design_review/workflow.lgwf").read_text(encoding="utf-8")
        implement_workflow_path = ROOT / "04_implement_steps_react/workflow.lgwf"
        self.assertTrue(implement_workflow_path.is_file())
        implement_workflow = implement_workflow_path.read_text(encoding="utf-8")

        self.assertNotIn("CODEX implement_steps_react", design_workflow)
        self.assertIn("PY prepare_implementation_context", design_workflow)
        self.assertNotIn("PY pre_implementation_audit_check", implement_workflow)
        self.assertNotIn("THEN pre_implementation_audit_check", implement_workflow)
        self.assertNotIn("REACT implement_steps_react MAX 3", implement_workflow)
        self.assertIn("STEP implement_initial_units", implement_workflow)
        self.assertIn("STEP repair_implementation", implement_workflow)
        self.assertIn("ENTRY implement_initial_units;", implement_workflow)
        self.assertNotIn("ENTRY FLOW implement_initial_units;", implement_workflow)
        self.assertIn('WORKFLOW "01_implement_units/workflow.lgwf"', implement_workflow)
        self.assertIn('WORKFLOW "02_repair_implementation_react/workflow.lgwf"', implement_workflow)
        self.assertNotIn("RESULT state.lgwf_wf_create.initial_implementation_result", implement_workflow)
        self.assertNotIn("RESULT state.lgwf_wf_create.repair_implementation_result", implement_workflow)
        self.assertIn("FLOW implement_initial_units", implement_workflow)
        self.assertIn("THEN repair_implementation", implement_workflow)
        self.assertNotIn("ACT CODEX", implement_workflow)
        repair_workflow = (ROOT / "04_implement_steps_react/02_repair_implementation_react/workflow.lgwf").read_text(
            encoding="utf-8"
        )
        self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
        self.assertNotIn("RESULT state.lgwf_wf_create.initial_repair_observe_result", repair_workflow)
        self.assertIn("REASON WORKFLOW reason_repair", repair_workflow)
        self.assertIn("ACT WORKFLOW act_repair", repair_workflow)
        self.assertIn("OBSERVE WORKFLOW observe_repair", repair_workflow)
        self.assertIn("DECIDE WORKFLOW decide_repair", repair_workflow)
        act_workflow = (ROOT / "04_implement_steps_react/01_implement_units/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY prepare_implementation_units", act_workflow)
        self.assertNotIn("CODEX prime_implementation_codex", act_workflow)
        self.assertNotIn('PROMPT "agents/prime_implementation_codex.md"', act_workflow)
        self.assertNotIn('KEEP_SESSION KEY "implementation_codex"', act_workflow)
        self.assertRegex(
            act_workflow,
            r"prepare_implementation_units\s+THEN\s+implement_each_unit",
        )
        self.assertIn("FOREACH implement_each_unit", act_workflow)
        self.assertIn('WORKFLOW "01_implement_one_unit/workflow.lgwf"', act_workflow)
        self.assertIn("PY merge_implementation_results", act_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_result.json"', act_workflow)
        unit_workflow = (
            ROOT / "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertIn("PY prepare_current_implementation_unit", unit_workflow)
        self.assertIn("CODEX implement_current_unit", unit_workflow)
        prepare_block = unit_workflow.split("CODEX implement_current_unit", 1)[0]
        implement_block = unit_workflow.split("CODEX implement_current_unit", 1)[1].split(
            "PY publish_current_implementation_unit_result",
            1,
        )[0]
        self.assertNotIn('CONTEXT workflow file "agents/spec.md"', unit_workflow)
        self.assertNotIn('READ workflow file "agents/spec.md";', unit_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/current_implementation_unit_context.json"', implement_block)
        self.assertNotIn(
            'CONTEXT workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            implement_block,
        )
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context"', implement_block)
        self.assertNotIn('KEEP_SESSION KEY "implementation_codex"', implement_block)
        self.assertNotIn('READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";', prepare_block)
        self.assertNotIn('READ workspace dir ".lgwf/create_reference_context";', prepare_block)
        self.assertNotIn(
            'READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";',
            implement_block,
        )
        self.assertNotIn('READ workspace dir ".lgwf/create_reference_context";', implement_block)
        self.assertNotIn("TARGET_DIRS state.lgwf_wf_create.current_implementation_unit_target_dirs", unit_workflow)
        self.assertNotIn("TARGET_FILES state.lgwf_wf_create.current_implementation_unit_target_files", unit_workflow)
        self.assertIn('WRITE workspace dir ".lgwf/implementation_stage";', unit_workflow)
        self.assertIn('OUTPUT_JSON ".lgwf/current_implementation_unit_result.json" AS_FILE', unit_workflow)
        self.assertNotIn('CONTEXT workflow file "resources/lgwf_dsl_authoring.md"', implement_block)
        self.assertNotIn('READ workflow file "resources/lgwf_dsl_authoring.md";', implement_block)
        repair_act_workflow = (
            ROOT / "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertIn('CONTEXT workspace file ".lgwf/implementation_repair_reason.json"', repair_act_workflow)
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context"', repair_act_workflow)
        self.assertNotIn(
            'CONTEXT workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            repair_act_workflow,
        )
        repair_reason_workflow = (
            ROOT / "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertIn('CONTEXT workspace file ".lgwf/implementation_audit_result.json"', repair_reason_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/implementation_observe.json"', repair_reason_workflow)
        for forbidden in (
            ".lgwf/create_reference_context",
            ".lgwf/implementation_context.json",
            ".lgwf/implementation_result.json",
            ".lgwf/scaffold_package_result.json",
            ".lgwf/step_designs.json",
        ):
            self.assertNotIn(forbidden, repair_reason_workflow)
        observe_workflow = (
            ROOT / "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertIn("PY audit_current_implementation", observe_workflow)
        self.assertIn('SCRIPT "scripts/audit_current_implementation.py"', observe_workflow)
        self.assertNotIn("CODEX observe_repair", observe_workflow)
        self.assertNotIn('PROMPT "agents/observe_repair.md"', observe_workflow)
        self.assertNotIn('workflow file "agents/spec.md"', observe_workflow)
        self.assertNotIn('READ workflow file "agents/spec.md";', observe_workflow)
        self.assertNotIn("INSTRUCTION state.lgwf_wf_create.implementation_audit_result", observe_workflow)
        self.assertIn('workspace file ".lgwf/implementation_audit_result.json"', observe_workflow)
        self.assertNotIn('workspace file ".lgwf/scaffold_package_result.json"', observe_workflow)
        self.assertIn('READ workspace file ".lgwf/step_designs.json";', observe_workflow)
        self.assertNotIn('OUTPUT_JSON ".lgwf/implementation_observe.json" AS_FILE', observe_workflow)
        self.assertIn("FLOW audit_current_implementation", observe_workflow)
        self.assertNotIn("THEN observe_repair", observe_workflow)
        self.assertIn("UPDATES_STATE", observe_workflow)
        self.assertIn('READ workspace file ".lgwf/implementation_audit_result.json";', repair_workflow)
        reason_prompt = (
            ROOT / "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/agents/reason_repair.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".lgwf/implementation_audit_result.json", reason_prompt)
        self.assertIn("原始 Python audit 结果", reason_prompt)
        audit_script = (
            ROOT
            / "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/scripts/audit_current_implementation.py"
        ).read_text(encoding="utf-8")
        self.assertIn("lgwf_dsl_cli", audit_script)
        self.assertNotIn("lgwf.py", audit_script)
        self.assertIn("implementation_audit_result.json", audit_script)
        self.assertIn("check_workflow_resource_references", audit_script)
        decide_workflow = (
            ROOT / "04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertNotIn("CODEX decide_repair", decide_workflow)
        self.assertIn("PY write_repair_decision", decide_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_repair_decision_analysis.json";', decide_workflow)

    def test_scaffold_template_spec_is_bound_to_template_and_react_prompts(self) -> None:
        spec_path = ROOT / "02_confirm_business_flow/03_scaffold_package/resources/scaffold_template_spec.md"
        template_path = ROOT / "02_confirm_business_flow/03_scaffold_package/resources/scaffold_package_template.json"
        contract_path = ROOT / "02_confirm_business_flow/03_scaffold_package/resources/scaffold_result_contract.md"
        step_workflow = (ROOT / "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf").read_text(encoding="utf-8")
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
            "02_confirm_business_flow/03_scaffold_package/resources/scaffold_template_spec.md",
            "02_confirm_business_flow/03_scaffold_package/resources/scaffold_result_contract.md",
            "02_confirm_business_flow/03_scaffold_package/resources/scaffold_package_template.json",
        }
        contracts = json.loads((ROOT / "artifact_contracts.json").read_text(encoding="utf-8"))
        script_writes = contracts["script_writes"]["prepare_dsl_reference_context"]
        step_design_workflow_text = step_workflow
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context"', step_design_workflow_text)
        self.assertNotIn(
            'CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"',
            step_design_workflow_text,
        )
        self.assertNotIn('CONTEXT workspace file ".lgwf/create_reference_context/index.md"', step_design_workflow_text)
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context/scaffold"', step_design_workflow_text)
        step_act_block = step_workflow.split('PROMPT "agents/act_step_design_repair.md"', 1)[-1]
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context"', step_act_block)
        self.assertNotIn('CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"', step_act_block)
        reference_index = (
            ROOT / "03_confirm_step_designs/01_reference_context/resources/step_design_reference_index.md"
        ).read_text(encoding="utf-8")
        for resource in scaffold_resources:
            self.assertTrue((ROOT / resource).is_file(), resource)
            filename = Path(resource).name
            self.assertNotIn(f".lgwf/create_reference_context/scaffold/{filename}", script_writes)
            self.assertNotIn(f"scaffold/{filename}", reference_index)
        self.assertIn(
            ".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md",
            script_writes,
        )
        self.assertIn(
            ".lgwf/create_reference_context/implementation-reference-index.md",
            script_writes,
        )
        self.assertIn("workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md", reference_index)

        prompt = read_step_design_prompts()
        self.assertIn("reference index", prompt)
        self.assertNotIn(".lgwf/create_reference_context/index.md", prompt)
        self.assertIn("scaffold_plan", prompt)
        self.assertIn("scaffold plan", prompt)
        self.assertIn("package_profile", prompt)
        self.assertNotIn("02_confirm_business_flow/03_scaffold_package/resources/scaffold_template_spec.md", prompt)
        self.assertNotIn(".lgwf/create_reference_context/scaffold", prompt)

        implementation_prompt = "\n".join(
            (
                (ROOT / "04_implement_steps_react/02_repair_implementation_react/agents/spec.md").read_text(
                    encoding="utf-8"
                ),
                (ROOT / "04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md").read_text(
                    encoding="utf-8"
                ),
            )
        )
        self.assertNotIn(
            "02_confirm_business_flow/03_scaffold_package/resources/scaffold_template_spec.md",
            implementation_prompt,
        )
        self.assertNotIn(".lgwf/create_reference_context/scaffold", implementation_prompt)
        self.assertNotIn(".lgwf/scaffold_package_result.json", implementation_prompt)
        self.assertNotIn("implementation_reference_context", implementation_prompt)
        self.assertNotIn(".lgwf/create_reference_context/implementation-reference-index.md", implementation_prompt)
        self.assertNotIn(".lgwf/create_reference_context", implementation_prompt)
        self.assertNotIn("lgwf_dsl_contract", implementation_prompt)
        self.assertNotIn("resources/lgwf_dsl_authoring.md", implementation_prompt)
        self.assertIn("exact_content", implementation_prompt)
        self.assertNotIn(
            ".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md",
            implementation_prompt,
        )
        self.assertNotIn("scaffold_plan", implementation_prompt)
        self.assertIn("package_profile", implementation_prompt)

    def test_apply_scripts_write_confirmed_artifacts_and_reject_invalid_paths(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
                "create_requirements_approval.json",
                "create_requirements_proposal.json",
                "create_requirements.json",
                "apply_requirements",
                {"workflow_name": "demo", "target_package_root": "skills/demo"},
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/scripts/apply_confirmed.py",
                "business_flow_approval.json",
                "business_flow_proposal.json",
                "business_flow.json",
                "apply_business_flow",
                {"workflow_name": "demo", "stages": []},
            ),
            (
                "03_confirm_step_designs/03_step_design_review/scripts/apply_confirmed_step_designs.py",
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
