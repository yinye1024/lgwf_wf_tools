from __future__ import annotations

import py_compile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILES = ['wf/01_confirm_requirements/workflow.lgwf', 'wf/02_confirm_business_flow/workflow.lgwf', 'wf/03_confirm_step_designs/workflow.lgwf', 'wf/04_implement_steps_react/workflow.lgwf', 'wf/06_summarize_create_result/workflow.lgwf', 'wf/workflow.lgwf']
SCRIPT_ENTRIES = [{'workflow': 'wf/workflow.lgwf', 'script_path': 'scripts/prepare_post_fix_handoff.py', 'resolved_path': 'wf/scripts/prepare_post_fix_handoff.py'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'script_path': 'scripts/prepare_raw_intent_confirmation.py', 'resolved_path': 'wf/01_confirm_requirements/scripts/prepare_raw_intent_confirmation.py'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'script_path': 'scripts/apply_confirmed_raw_intent.py', 'resolved_path': 'wf/01_confirm_requirements/scripts/apply_confirmed_raw_intent.py'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'script_path': 'scripts/finish_raw_intent.py', 'resolved_path': 'wf/01_confirm_requirements/scripts/finish_raw_intent.py'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'script_path': 'scripts/prepare_requirements_confirmation.py', 'resolved_path': 'wf/01_confirm_requirements/scripts/prepare_requirements_confirmation.py'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'script_path': 'scripts/prepare_requirements_revision_confirmation.py', 'resolved_path': 'wf/01_confirm_requirements/scripts/prepare_requirements_revision_confirmation.py'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'script_path': 'scripts/apply_confirmed_requirements.py', 'resolved_path': 'wf/01_confirm_requirements/scripts/apply_confirmed_requirements.py'}, {'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'script_path': 'scripts/prepare_business_flow_confirmation.py', 'resolved_path': 'wf/02_confirm_business_flow/scripts/prepare_business_flow_confirmation.py'}, {'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'script_path': 'scripts/prepare_business_flow_revision_confirmation.py', 'resolved_path': 'wf/02_confirm_business_flow/scripts/prepare_business_flow_revision_confirmation.py'}, {'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'script_path': 'scripts/apply_confirmed_business_flow.py', 'resolved_path': 'wf/02_confirm_business_flow/scripts/apply_confirmed_business_flow.py'}, {'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'script_path': 'scripts/scaffold_package.py', 'resolved_path': 'wf/02_confirm_business_flow/scripts/scaffold_package.py'}, {'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'script_path': 'scripts/prepare_dsl_reference_context.py', 'resolved_path': 'wf/03_confirm_step_designs/scripts/prepare_dsl_reference_context.py'}, {'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'script_path': 'scripts/prepare_step_design_confirmation.py', 'resolved_path': 'wf/03_confirm_step_designs/scripts/prepare_step_design_confirmation.py'}, {'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'script_path': 'scripts/prepare_step_design_revision_confirmation.py', 'resolved_path': 'wf/03_confirm_step_designs/scripts/prepare_step_design_revision_confirmation.py'}, {'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'script_path': 'scripts/apply_confirmed_step_designs.py', 'resolved_path': 'wf/03_confirm_step_designs/scripts/apply_confirmed_step_designs.py'}, {'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'script_path': 'scripts/prepare_implementation_context.py', 'resolved_path': 'wf/03_confirm_step_designs/scripts/prepare_implementation_context.py'}, {'workflow': 'wf/04_implement_steps_react/workflow.lgwf', 'script_path': 'scripts/initialize_implementation_observe.py', 'resolved_path': 'wf/04_implement_steps_react/scripts/initialize_implementation_observe.py'}, {'workflow': 'wf/04_implement_steps_react/workflow.lgwf', 'script_path': 'scripts/decide_implementation.py', 'resolved_path': 'wf/04_implement_steps_react/scripts/decide_implementation.py'}, {'workflow': 'wf/06_summarize_create_result/workflow.lgwf', 'script_path': 'scripts/summarize_create_result.py', 'resolved_path': 'wf/06_summarize_create_result/scripts/summarize_create_result.py'}]
ROUTE_ENTRIES = []
APPROVAL_PERSIST_ENTRIES = [{'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'artifact': '.lgwf/raw_intent_approval.json'}, {'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'artifact': '.lgwf/create_requirements_approval.json'}, {'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'artifact': '.lgwf/business_flow_approval.json'}, {'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'artifact': '.lgwf/step_design_confirmation_record.json'}]
FORBIDDEN_PATTERNS = ["lgwf.py " + "run", "--workflow-" + "lgwf", "co" + "dex"]


class GeneratedScriptFlowE2ETest(unittest.TestCase):
    def workflow_text(self, relative: str) -> str:
        path = ROOT / relative
        self.assertTrue(path.exists(), f"workflow file missing: {relative}")
        return path.read_text(encoding="utf-8")

    def test_case_script_contracts_compile(self) -> None:
        self.assertTrue(SCRIPT_ENTRIES, "script contracts should not be empty")
        for entry in SCRIPT_ENTRIES:
            with self.subTest(script=entry["resolved_path"]):
                script_path = ROOT / entry["resolved_path"]
                self.assertTrue(script_path.exists(), f"script missing: {entry['resolved_path']}")
                py_compile.compile(str(script_path), doraise=True)

    def test_case_routes_declared(self) -> None:
        for route in ROUTE_ENTRIES:
            with self.subTest(route=route):
                text = self.workflow_text(route["workflow"])
                expected = f'WHEN "{route["value"]}" THEN {route["target"]}'
                self.assertIn(expected, text)

    def test_case_approval_persist_declared(self) -> None:
        for entry in APPROVAL_PERSIST_ENTRIES:
            with self.subTest(artifact=entry):
                text = self.workflow_text(entry["workflow"])
                self.assertIn(f'PERSIST "{entry["artifact"]}"', text)

    def test_case_no_runtime_or_model_launch_guard(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)


if __name__ == "__main__":
    unittest.main()
