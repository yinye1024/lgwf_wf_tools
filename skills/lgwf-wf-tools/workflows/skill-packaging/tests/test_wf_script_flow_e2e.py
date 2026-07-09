from __future__ import annotations

import py_compile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILES = ['wf/01_prepare_packaging_request/workflow.lgwf', 'wf/02_preflight_packaging_plan/workflow.lgwf', 'wf/03_confirm_packaging_plan/workflow.lgwf', 'wf/04_materialize_packaged_skill/workflow.lgwf', 'wf/05_verify_packaged_skill/workflow.lgwf', 'wf/06_summarize_packaging_result/workflow.lgwf', 'wf/workflow.lgwf']
SCRIPT_ENTRIES = [{'workflow': 'wf/01_prepare_packaging_request/workflow.lgwf', 'script_path': 'scripts/normalize_packaging_request.py', 'resolved_path': 'wf/01_prepare_packaging_request/scripts/normalize_packaging_request.py'}, {'workflow': 'wf/01_prepare_packaging_request/workflow.lgwf', 'script_path': 'scripts/resolve_runtime_source.py', 'resolved_path': 'wf/01_prepare_packaging_request/scripts/resolve_runtime_source.py'}, {'workflow': 'wf/01_prepare_packaging_request/workflow.lgwf', 'script_path': 'scripts/freeze_write_scope.py', 'resolved_path': 'wf/01_prepare_packaging_request/scripts/freeze_write_scope.py'}, {'workflow': 'wf/02_preflight_packaging_plan/workflow.lgwf', 'script_path': 'scripts/validate_source_skill_structure.py', 'resolved_path': 'wf/02_preflight_packaging_plan/scripts/validate_source_skill_structure.py'}, {'workflow': 'wf/02_preflight_packaging_plan/workflow.lgwf', 'script_path': 'scripts/validate_runtime_source.py', 'resolved_path': 'wf/02_preflight_packaging_plan/scripts/validate_runtime_source.py'}, {'workflow': 'wf/02_preflight_packaging_plan/workflow.lgwf', 'script_path': 'scripts/inspect_output_parent_state.py', 'resolved_path': 'wf/02_preflight_packaging_plan/scripts/inspect_output_parent_state.py'}, {'workflow': 'wf/02_preflight_packaging_plan/workflow.lgwf', 'script_path': 'scripts/draft_packaging_plan_proposal.py', 'resolved_path': 'wf/02_preflight_packaging_plan/scripts/draft_packaging_plan_proposal.py'}, {'workflow': 'wf/03_confirm_packaging_plan/workflow.lgwf', 'script_path': 'scripts/prepare_packaging_plan_confirmation.py', 'resolved_path': 'wf/03_confirm_packaging_plan/scripts/prepare_packaging_plan_confirmation.py'}, {'workflow': 'wf/03_confirm_packaging_plan/workflow.lgwf', 'script_path': 'scripts/prepare_packaging_plan_revision_confirmation.py', 'resolved_path': 'wf/03_confirm_packaging_plan/scripts/prepare_packaging_plan_revision_confirmation.py'}, {'workflow': 'wf/03_confirm_packaging_plan/workflow.lgwf', 'script_path': 'scripts/apply_confirmed_packaging_plan.py', 'resolved_path': 'wf/03_confirm_packaging_plan/scripts/apply_confirmed_packaging_plan.py'}, {'workflow': 'wf/04_materialize_packaged_skill/workflow.lgwf', 'script_path': 'scripts/copy_source_skill_tree.py', 'resolved_path': 'wf/04_materialize_packaged_skill/scripts/copy_source_skill_tree.py'}, {'workflow': 'wf/04_materialize_packaged_skill/workflow.lgwf', 'script_path': 'scripts/embed_bundled_runtime.py', 'resolved_path': 'wf/04_materialize_packaged_skill/scripts/embed_bundled_runtime.py'}, {'workflow': 'wf/04_materialize_packaged_skill/workflow.lgwf', 'script_path': 'scripts/generate_local_runner.py', 'resolved_path': 'wf/04_materialize_packaged_skill/scripts/generate_local_runner.py'}, {'workflow': 'wf/04_materialize_packaged_skill/workflow.lgwf', 'script_path': 'scripts/write_packaging_manifest.py', 'resolved_path': 'wf/04_materialize_packaged_skill/scripts/write_packaging_manifest.py'}, {'workflow': 'wf/04_materialize_packaged_skill/workflow.lgwf', 'script_path': 'scripts/record_materialization_summary.py', 'resolved_path': 'wf/04_materialize_packaged_skill/scripts/record_materialization_summary.py'}, {'workflow': 'wf/05_verify_packaged_skill/workflow.lgwf', 'script_path': 'scripts/validate_output_structure.py', 'resolved_path': 'wf/05_verify_packaged_skill/scripts/validate_output_structure.py'}, {'workflow': 'wf/05_verify_packaged_skill/workflow.lgwf', 'script_path': 'scripts/validate_packaging_manifest.py', 'resolved_path': 'wf/05_verify_packaged_skill/scripts/validate_packaging_manifest.py'}, {'workflow': 'wf/05_verify_packaged_skill/workflow.lgwf', 'script_path': 'scripts/validate_embedded_runtime.py', 'resolved_path': 'wf/05_verify_packaged_skill/scripts/validate_embedded_runtime.py'}, {'workflow': 'wf/05_verify_packaged_skill/workflow.lgwf', 'script_path': 'scripts/run_authoring_audit_smoke.py', 'resolved_path': 'wf/05_verify_packaged_skill/scripts/run_authoring_audit_smoke.py'}, {'workflow': 'wf/05_verify_packaged_skill/workflow.lgwf', 'script_path': 'scripts/record_package_validation.py', 'resolved_path': 'wf/05_verify_packaged_skill/scripts/record_package_validation.py'}, {'workflow': 'wf/06_summarize_packaging_result/workflow.lgwf', 'script_path': 'scripts/summarize_packaging_result.py', 'resolved_path': 'wf/06_summarize_packaging_result/scripts/summarize_packaging_result.py'}, {'workflow': 'wf/06_summarize_packaging_result/workflow.lgwf', 'script_path': 'scripts/emit_packaging_result_report.py', 'resolved_path': 'wf/06_summarize_packaging_result/scripts/emit_packaging_result_report.py'}]
ROUTE_ENTRIES = []
APPROVAL_PERSIST_ENTRIES = [{'workflow': 'wf/03_confirm_packaging_plan/workflow.lgwf', 'artifact': '.lgwf/packaging_plan_approval.json'}]
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
