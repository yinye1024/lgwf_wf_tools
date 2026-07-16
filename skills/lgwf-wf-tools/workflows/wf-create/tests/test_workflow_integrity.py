from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROOT = PACKAGE_ROOT / "wf"
sys.dont_write_bytecode = True


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class WorkflowCreateIntegrityTest(unittest.TestCase):
    def test_confirm_requirements_files_are_grouped_by_business_flow(self) -> None:
        base = ROOT / "01_confirm_requirements"
        expected_files = (
            "01_raw_intent/workflow.lgwf",
            "01_raw_intent/README.md",
            "01_raw_intent/agents/confirm_raw_intent.md",
            "01_raw_intent/scripts/prepare_confirmation.py",
            "01_raw_intent/scripts/apply_confirmed.py",
            "02_requirements_proposal/workflow.lgwf",
            "02_requirements_proposal/README.md",
            "02_requirements_proposal/agents/propose_requirements.md",
            "02_requirements_proposal/scripts/assert_quality_gate.py",
            "02_requirements_proposal/scripts/decide_react.py",
            "02_requirements_proposal/scripts/prepare_react_feedback.py",
            "02_requirements_proposal/scripts/prepare_react_context.py",
            "02_requirements_proposal/scripts/validate_proposal.py",
            "03_requirements_review/workflow.lgwf",
            "03_requirements_review/README.md",
            "03_requirements_review/agents/confirm_requirements.md",
            "03_requirements_review/agents/revise_requirements.md",
            "03_requirements_review/scripts/prepare_confirmation.py",
            "03_requirements_review/scripts/prepare_revision_confirmation.py",
            "03_requirements_review/scripts/apply_confirmed.py",
        )
        for relative in expected_files:
            with self.subTest(relative=relative):
                self.assertTrue((base / relative).is_file(), relative)

        old_locations = (
            "confirm_raw_intent.md",
            "confirm_requirements.md",
            "revise_requirements.md",
            "agents/propose_requirements.md",
            "agents/propose_requirements_spec.md",
            "scripts/prepare_raw_intent_confirmation.py",
            "scripts/apply_confirmed_raw_intent.py",
            "scripts/finish_raw_intent.py",
            "scripts/validate_requirements_proposal.py",
            "scripts/prepare_requirements_confirmation.py",
            "scripts/prepare_requirements_revision_confirmation.py",
            "scripts/apply_confirmed_requirements.py",
            "raw_intent/workflow.lgwf",
            "raw_intent/confirm_raw_intent.md",
            "requirements_proposal/workflow.lgwf",
            "requirements_review/workflow.lgwf",
            "requirements_review/confirm_requirements.md",
            "requirements_review/revise_requirements.md",
            "02_requirements_proposal/agents/spec.md",
        )
        for relative in old_locations:
            with self.subTest(old_location=relative):
                self.assertFalse((base / relative).exists(), relative)

    def test_confirm_requirements_parent_workflow_only_orchestrates_business_subflows(self) -> None:
        text = (ROOT / "01_confirm_requirements/workflow.lgwf").read_text(encoding="utf-8")
        for snippet in (
            'WORKFLOW "01_raw_intent/workflow.lgwf"',
            'WORKFLOW "02_requirements_proposal/workflow.lgwf"',
            'WORKFLOW "03_requirements_review/workflow.lgwf"',
            "FLOW raw_intent\n  THEN requirements_proposal\n  THEN requirements_review;",
        ):
            self.assertIn(snippet, text)
        for direct_node in ("PY ", "CODEX ", "REVIEW "):
            self.assertNotIn(direct_node, text)

    def test_confirm_requirements_business_subflows_declare_local_responsibilities(self) -> None:
        expectations = {
            "raw_intent": (
                "PY prepare_raw_intent_confirmation",
                "REVIEW confirm_raw_intent",
                "PY apply_confirmed_raw_intent",
                "PY finish_raw_intent",
                'SCRIPT "scripts/prepare_confirmation.py"',
                'PROMPT_REF "agents/confirm_raw_intent.md"',
            ),
            "requirements_proposal": (
                "REACT requirements_proposal_react",
                "PY prepare_requirements_proposal_react_feedback",
                "ACT CODEX",
                "OBSERVE PY",
                "PY assert_requirements_proposal_quality_gate",
                'PROMPT "agents/propose_requirements.md"',
                'SCRIPT "scripts/validate_proposal.py"',
            ),
            "requirements_review": (
                "PY prepare_requirements_confirmation",
                "REVIEW confirm_requirements",
                "PY prepare_requirements_revision_confirmation",
                "PY apply_confirmed_requirements",
                'SCRIPT "scripts/prepare_confirmation.py"',
                'PROMPT_REF "agents/confirm_requirements.md"',
            ),
        }
        for subflow, snippets in expectations.items():
            subflow_dir = {
                "raw_intent": "01_raw_intent",
                "requirements_proposal": "02_requirements_proposal",
                "requirements_review": "03_requirements_review",
            }[subflow]
            workflow = (ROOT / f"01_confirm_requirements/{subflow_dir}/workflow.lgwf").read_text(encoding="utf-8")
            readme = (ROOT / f"01_confirm_requirements/{subflow_dir}/README.md").read_text(encoding="utf-8")
            for snippet in snippets:
                with self.subTest(subflow=subflow, snippet=snippet):
                    self.assertIn(snippet, workflow)
            for heading in ("职责", "输入", "输出", "产物", "验证", "禁止事项"):
                with self.subTest(subflow=subflow, heading=heading):
                    self.assertIn(heading, readme)

    def test_confirm_business_flow_files_are_grouped_by_business_flow(self) -> None:
        base = ROOT / "02_confirm_business_flow"
        expected_files = (
            "workflow.lgwf",
            "README.md",
            "01_business_flow_proposal/workflow.lgwf",
            "01_business_flow_proposal/README.md",
            "01_business_flow_proposal/agents/propose_business_flow.md",
            "01_business_flow_proposal/resources/README.md",
            "02_business_flow_review/workflow.lgwf",
            "02_business_flow_review/README.md",
            "02_business_flow_review/agents/confirm_business_flow.md",
            "02_business_flow_review/agents/revise_business_flow.md",
            "02_business_flow_review/scripts/prepare_confirmation.py",
            "02_business_flow_review/scripts/prepare_revision_confirmation.py",
            "02_business_flow_review/scripts/apply_confirmed.py",
            "02_business_flow_review/resources/business_flow_approval_example.json",
            "03_scaffold_package/workflow.lgwf",
            "03_scaffold_package/README.md",
            "03_scaffold_package/scripts/scaffold_package.py",
            "03_scaffold_package/resources/scaffold_template_spec.md",
            "03_scaffold_package/resources/scaffold_result_contract.md",
            "03_scaffold_package/resources/scaffold_package_template.json",
        )
        for relative in expected_files:
            with self.subTest(relative=relative):
                self.assertTrue((base / relative).is_file(), relative)

        old_locations = (
            "confirm_business_flow.md",
            "revise_business_flow.md",
            "agents",
            "resources",
            "scripts",
            "01_business_flow_proposal/agents/spec.md",
        )
        for relative in old_locations:
            with self.subTest(old_location=relative):
                self.assertFalse((base / relative).exists(), relative)

    def test_confirm_business_flow_parent_workflow_only_orchestrates_business_subflows(self) -> None:
        text = (ROOT / "02_confirm_business_flow/workflow.lgwf").read_text(encoding="utf-8")
        for snippet in (
            'WORKFLOW "01_business_flow_proposal/workflow.lgwf"',
            'WORKFLOW "02_business_flow_review/workflow.lgwf"',
            'WORKFLOW "03_scaffold_package/workflow.lgwf"',
            "FLOW business_flow_proposal\n  THEN business_flow_review\n  THEN scaffold_package;",
        ):
            self.assertIn(snippet, text)
        for direct_node in ("PY ", "CODEX ", "REVIEW "):
            self.assertNotIn(direct_node, text)

    def test_confirm_business_flow_subflows_declare_local_responsibilities(self) -> None:
        expectations = {
            "business_flow_proposal": (
                "ENTRY prepare_business_flow_context",
                "PY prepare_business_flow_context",
                'SCRIPT "scripts/prepare_business_flow_context.py"',
                "CODEX propose_business_flow",
                'CONTEXT workspace file ".lgwf/business_flow_proposal_context.json"',
                'PROMPT "agents/propose_business_flow.md"',
                "ANALYSIS_DIRS state.lgwf_wf_create.creation_context_dirs",
                "ANALYSIS_FILES state.lgwf_wf_create.creation_context_files",
                'OUTPUT_JSON ".lgwf/business_flow_proposal.json" AS_FILE',
                'WRITE workspace file ".lgwf/business_flow_proposal.json";',
            ),
            "business_flow_review": (
                "PY prepare_business_flow_confirmation",
                "REVIEW confirm_business_flow",
                "PY prepare_business_flow_revision_confirmation",
                "PY apply_confirmed_business_flow",
                'SCRIPT "scripts/prepare_confirmation.py"',
                'PROMPT_REF "agents/confirm_business_flow.md"',
            ),
            "scaffold_package": (
                "PY scaffold_package",
                'SCRIPT "scripts/scaffold_package.py"',
                'WRITE workspace file ".lgwf/scaffold_package_result.json"',
            ),
        }
        for subflow, snippets in expectations.items():
            subflow_dir = {
                "business_flow_proposal": "01_business_flow_proposal",
                "business_flow_review": "02_business_flow_review",
                "scaffold_package": "03_scaffold_package",
            }[subflow]
            workflow = (ROOT / f"02_confirm_business_flow/{subflow_dir}/workflow.lgwf").read_text(encoding="utf-8")
            readme = (ROOT / f"02_confirm_business_flow/{subflow_dir}/README.md").read_text(encoding="utf-8")
            for snippet in snippets:
                with self.subTest(subflow=subflow, snippet=snippet):
                    self.assertIn(snippet, workflow)
            for heading in ("职责", "输入", "输出", "产物", "验证", "禁止事项"):
                with self.subTest(subflow=subflow, heading=heading):
                    self.assertIn(heading, readme)

    def test_confirm_step_designs_files_are_grouped_by_business_flow(self) -> None:
        base = ROOT / "03_confirm_step_designs"
        expected_files = (
            "workflow.lgwf",
            "README.md",
            "artifact_contracts.json",
            "01_reference_context/workflow.lgwf",
            "01_reference_context/README.md",
            "01_reference_context/artifact_contracts.json",
            "01_reference_context/scripts/prepare_dsl_reference_context.py",
            "02_step_design_proposal/workflow.lgwf",
            "02_step_design_proposal/README.md",
            "02_step_design_proposal/agents/generate_step_designs.md",
            "02_step_design_proposal/agents/reason_step_design_repair.md",
            "02_step_design_proposal/agents/act_step_design_repair.md",
            "02_step_design_proposal/resources/step_designs_proposal.schema.json",
            "02_step_design_proposal/resources/step_designs_passing_example.json",
            "02_step_design_proposal/scripts/build_step_design_contract.py",
            "02_step_design_proposal/scripts/generate_step_designs_proposal.py",
            "02_step_design_proposal/scripts/normalize_step_designs_proposal.py",
            "02_step_design_proposal/scripts/validate_step_designs_structure.py",
            "02_step_design_proposal/scripts/route_step_design_repair_entry.py",
            "02_step_design_proposal/scripts/decide_step_designs.py",
            "02_step_design_proposal/scripts/assert_quality_gate.py",
            "03_step_design_review/workflow.lgwf",
            "03_step_design_review/README.md",
            "03_step_design_review/artifact_contracts.json",
            "03_step_design_review/scripts/apply_validated_step_designs.py",
            "03_step_design_review/scripts/prepare_implementation_context.py",
        )
        for relative in expected_files:
            with self.subTest(relative=relative):
                self.assertTrue((base / relative).is_file(), relative)

        old_locations = (
            "agents",
            "resources",
            "scripts",
            "confirm_step_designs.md",
            "revise_step_designs.md",
            "03_step_design_review/agents/confirm_step_designs.md",
            "03_step_design_review/agents/revise_step_designs.md",
            "03_step_design_review/scripts/prepare_step_design_confirmation.py",
            "03_step_design_review/scripts/prepare_step_design_revision_confirmation.py",
            "03_step_design_review/scripts/apply_confirmed_step_designs.py",
            "03_step_design_review/resources/step_design_approval_example.json",
            "02_step_design_proposal/agents/design_steps_react.md",
            "02_step_design_proposal/scripts/prepare_react_context.py",
            "02_step_design_proposal/scripts/validate_step_designs_proposal.py",
            "02_step_design_proposal/scripts/decide_react.py",
            "02_step_design_proposal/01_reason_step_designs",
            "02_step_design_proposal/02_act_step_designs",
            "02_step_design_proposal/03_observe_step_designs",
            "02_step_design_proposal/04_decide_step_designs",
        )
        for relative in old_locations:
            with self.subTest(old_location=relative):
                self.assertFalse((base / relative).exists(), relative)

    def test_confirm_step_designs_subflows_declare_local_responsibilities(self) -> None:
        expectations = {
            "reference_context": (
                "PY prepare_dsl_reference_context",
                'SCRIPT "scripts/prepare_dsl_reference_context.py"',
                'WRITE workspace file ".lgwf/create_reference_context/step-design-reference-index.md"',
                'WRITE workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            ),
            "step_design_proposal": (
                "ENTRY build_step_design_contract",
                "PY build_step_design_contract",
                "CODEX generate_step_designs",
                "PY normalize_step_designs_proposal",
                "PY validate_step_designs_initial",
                "PY route_step_design_repair_entry",
                "REACT repair_step_designs_proposal",
                "REASON CODEX",
                "ACT CODEX",
                "OBSERVE PY",
                "DECIDE PY",
                "PY assert_step_designs_proposal_quality_gate",
                'PROMPT "agents/generate_step_designs.md"',
                'PROMPT "agents/reason_step_design_repair.md"',
                'PROMPT "agents/act_step_design_repair.md"',
                'CONTEXT workspace file ".lgwf/step_design_authoring_context.json"',
                'CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"',
                'CONTEXT workspace dir ".lgwf/create_reference_context"',
                'OUTPUT_JSON ".lgwf/step_designs_proposal.json" AS_FILE',
                'READ workspace file ".lgwf/create_reference_context/step-design-reference-index.md";',
                'READ workspace dir ".lgwf/create_reference_context";',
                'READ workspace file ".lgwf/step_design_validation_contract.json";',
                'WRITE workspace file ".lgwf/step_design_authoring_context.json";',
                'READ workflow file "resources/step_designs_proposal.schema.json"',
                'READ workflow file "resources/step_designs_passing_example.json"',
                'EDIT_FILE ".lgwf/step_designs_proposal.json"',
                'SCRIPT "scripts/build_step_design_contract.py"',
                'SCRIPT "scripts/normalize_step_designs_proposal.py"',
                'SCRIPT "scripts/validate_step_designs_structure.py"',
                'SCRIPT "scripts/route_step_design_repair_entry.py"',
                'SCRIPT "scripts/decide_step_designs.py"',
                'READ workspace file ".lgwf/scaffold_package_result.json";',
            ),
            "step_design_review": (
                "ENTRY apply_validated_step_designs",
                "PY apply_validated_step_designs",
                "PY prepare_implementation_context",
                'SCRIPT "scripts/apply_validated_step_designs.py"',
                'READ workspace file ".lgwf/step_design_observation.json";',
                'WRITE workspace file ".lgwf/step_designs.json";',
            ),
        }
        for subflow, snippets in expectations.items():
            subflow_dir = {
                "reference_context": "01_reference_context",
                "step_design_proposal": "02_step_design_proposal",
                "step_design_review": "03_step_design_review",
            }[subflow]
            workflow = (ROOT / f"03_confirm_step_designs/{subflow_dir}/workflow.lgwf").read_text(encoding="utf-8")
            readme = (ROOT / f"03_confirm_step_designs/{subflow_dir}/README.md").read_text(encoding="utf-8")
            for snippet in snippets:
                with self.subTest(subflow=subflow, snippet=snippet):
                    self.assertIn(snippet, workflow)
            for heading in ("职责", "输入", "输出", "产物", "验证", "禁止事项"):
                with self.subTest(subflow=subflow, heading=heading):
                    self.assertIn(heading, readme)

    def test_confirm_step_designs_parent_workflow_only_orchestrates_business_subflows(self) -> None:
        text = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        for snippet in (
            'WORKFLOW "01_reference_context/workflow.lgwf"',
            'WORKFLOW "02_step_design_proposal/workflow.lgwf"',
            'WORKFLOW "03_step_design_review/workflow.lgwf"',
            "FLOW reference_context\n  THEN step_design_proposal\n  THEN step_design_review;",
        ):
            self.assertIn(snippet, text)
        for direct_node in ("PY ", "CODEX ", "REVIEW "):
            self.assertNotIn(direct_node, text)

    def test_step_design_stage_uses_only_confirmed_business_inputs(self) -> None:
        parent = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        proposal = (ROOT / "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf").read_text(
            encoding="utf-8"
        )
        prompt = "\n".join(
            (
                (
                    ROOT
                    / "03_confirm_step_designs/02_step_design_proposal/agents/generate_step_designs.md"
                ).read_text(encoding="utf-8"),
                (
                    ROOT
                    / "03_confirm_step_designs/02_step_design_proposal/agents/reason_step_design_repair.md"
                ).read_text(encoding="utf-8"),
                (
                    ROOT
                    / "03_confirm_step_designs/02_step_design_proposal/agents/act_step_design_repair.md"
                ).read_text(encoding="utf-8"),
            )
        )
        validator = (
            ROOT
            / "03_confirm_step_designs/02_step_design_proposal/scripts/validate_step_designs_structure.py"
        ).read_text(encoding="utf-8")

        combined_workflow = parent + "\n" + proposal
        for forbidden in (
            "state.lgwf_wf_create.creation_context_dirs",
            "state.lgwf_wf_create.creation_context_files",
            ".lgwf/business_flow_proposal.json",
        ):
            self.assertNotIn(forbidden, combined_workflow)
            self.assertNotIn(forbidden, prompt)
        self.assertNotIn('"business_flow_proposal.json"', validator)
        self.assertIn("已确认业务流", prompt)
        self.assertIn('"business_flow.json"', validator)

    def test_all_workflow_resource_references_exist(self) -> None:
        patterns = (
            r'WORKFLOW "([^"]+)"',
            r'PROMPT "([^"]+)"',
            r'PROMPT_REF "([^"]+)"',
            r'SCRIPT "([^"]+)"',
        )
        for workflow in ROOT.rglob("workflow.lgwf"):
            text = workflow.read_text(encoding="utf-8")
            for pattern in patterns:
                for relative in re.findall(pattern, text):
                    with self.subTest(workflow=workflow.relative_to(ROOT).as_posix(), relative=relative):
                        self.assertFalse(Path(relative).is_absolute())
                        self.assertNotIn("..", Path(relative).parts)
                        self.assertTrue((workflow.parent / relative).exists(), relative)

    def test_sub_approval_workflows_have_persist_and_decision_routes(self) -> None:
        expectations = (
            (
                "01_confirm_requirements/03_requirements_review/workflow.lgwf",
                "confirm_requirements",
                "prepare_requirements_revision_confirmation",
                "apply_confirmed_requirements",
                ".lgwf/create_requirements_approval.json",
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/workflow.lgwf",
                "confirm_business_flow",
                "prepare_business_flow_revision_confirmation",
                "apply_confirmed_business_flow",
                ".lgwf/business_flow_approval.json",
            ),
        )
        for relative, approval, apply_revision, apply_node, persist in expectations:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(f"REVIEW {approval}", text)
            self.assertIn('OPTIONS ["approve", "revise", "reject"]', text)
            self.assertIn(f'PERSIST "{persist}"', text)
            self.assertIn(f"PY {apply_revision}", text)
            self.assertIn("FLOW {", text)
            self.assertIn(approval, text)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', text)
            self.assertIn(f'WHEN "revise" THEN {apply_revision}', text)
            self.assertIn(f"{apply_revision}\n  THEN {approval}", text)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', text)
            self.assertIn('WHEN "reject" THEN FAIL_ALL', text)

        step_review = (ROOT / "03_confirm_step_designs/03_step_design_review/workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("REVIEW confirm_step_designs", step_review)
        self.assertNotIn('OPTIONS ["approve", "revise", "reject"]', step_review)
        self.assertNotIn("PERSIST", step_review)
        self.assertIn("PY apply_validated_step_designs", step_review)
        self.assertIn("apply_validated_step_designs\n  THEN prepare_implementation_context", step_review)

    def test_raw_intent_approval_is_persisted_without_decision_routing(self) -> None:
        text = (ROOT / "01_confirm_requirements/01_raw_intent/workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("APPROVAL collect_raw_intent", text)
        self.assertIn("PY prepare_raw_intent_confirmation", text)
        self.assertIn("REVIEW confirm_raw_intent", text)
        self.assertIn('PERSIST ".lgwf/raw_intent_approval.json"', text)
        self.assertIn("PY apply_confirmed_raw_intent", text)
        self.assertIn('WRITE workspace file ".lgwf/raw_intent_request.json"', text)
        self.assertIn("prepare_raw_intent_confirmation", text)
        self.assertIn("THEN confirm_raw_intent", text)
        self.assertIn('WHEN "approve" THEN apply_confirmed_raw_intent', text)
        self.assertIn("THEN finish_raw_intent", text)

    def test_apply_scripts_reject_non_approve_decisions(self) -> None:
        cases = (
            ("01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py", "create_requirements_approval.json", "create_requirements.json"),
            ("02_confirm_business_flow/02_business_flow_review/scripts/apply_confirmed.py", "business_flow_approval.json", "business_flow.json"),
        )
        for relative, approval_name, output_name in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"decision": "revise", "target_package_root": "skills/demo"}),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    module.write_confirmed_artifact(root)
                self.assertFalse((lgwf_dir / output_name).exists())

    def test_apply_scripts_use_current_proposal_after_revision_applied(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
                "create_requirements_approval.json",
                "create_requirements_proposal.json",
                "create_requirements.json",
                {"workflow_name": "demo", "target_package_root": "skills/demo"},
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/scripts/apply_confirmed.py",
                "business_flow_approval.json",
                "business_flow_proposal.json",
                "business_flow.json",
                {"workflow_name": "demo", "stages": [{"stage_id": "scaffold"}]},
            ),
        )
        for relative, approval_name, proposal_name, output_name, confirmed in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_revision"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / proposal_name).write_text(json.dumps(confirmed), encoding="utf-8")
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"decision": "approve"}),
                    encoding="utf-8",
                )
                result = module.write_confirmed_artifact(root)
                artifact = next(value for value in result.values() if isinstance(value, dict) and "artifact_path" in value)
                self.assertEqual(artifact["artifact_path"], f".lgwf/{output_name}")
                self.assertEqual(artifact["source_approval_file"], f".lgwf/{approval_name}")
                self.assertEqual(artifact["confirmed"], confirmed)
                self.assertNotIn("approval", artifact)

    def test_apply_scripts_reject_missing_fixed_proposal(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
                "create_requirements_approval.json",
                "create_requirements.json",
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/scripts/apply_confirmed.py",
                "business_flow_approval.json",
                "business_flow.json",
            ),
        )
        for relative, approval_name, output_name in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_approval_field"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"approval": "approve"}),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    module.write_confirmed_artifact(root)
                self.assertFalse((lgwf_dir / output_name).exists())

    def test_confirmed_runtime_artifacts_are_reported_separately_from_source_files(self) -> None:
        summary_module = load_module(
            ROOT / "06_summarize_create_result/scripts/summarize_create_result.py",
            "summary_integrity",
        )
        summary = summary_module.build_summary({})
        self.assertIn(".lgwf/create_requirements.json", summary["runtime_artifacts"])
        self.assertIn(".lgwf/business_flow.json", summary["runtime_artifacts"])
        self.assertIn(".lgwf/step_designs.json", summary["runtime_artifacts"])
        self.assertNotIn(".lgwf/implementation_audit_result.json", summary["runtime_artifacts"])
        self.assertNotIn(".lgwf/implementation_observe.json", summary["runtime_artifacts"])
        self.assertNotIn(".lgwf/implementation_decision.json", summary["runtime_artifacts"])
        self.assertNotIn(".lgwf/create_requirements.json", summary["produced_files"])

    def test_apply_scripts_share_common_confirmation_helpers(self) -> None:
        for relative in (
            "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
            "02_confirm_business_flow/02_business_flow_review/scripts/apply_confirmed.py",
            "03_confirm_step_designs/03_step_design_review/scripts/apply_validated_step_designs.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("from confirmation_io import", text)
            self.assertIn("shared", text)

    def test_step_design_and_implementation_use_dsl_assist_context(self) -> None:
        root_workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        parent_workflow = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        reference_workflow = (ROOT / "03_confirm_step_designs/01_reference_context/workflow.lgwf").read_text(
            encoding="utf-8"
        )
        proposal_workflow = (ROOT / "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf").read_text(
            encoding="utf-8"
        )
        implementation_workflow = (ROOT / "04_implement_steps_react/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('WORKFLOW "01_reference_context/workflow.lgwf"', parent_workflow)
        self.assertIn('WORKFLOW "02_step_design_proposal/workflow.lgwf"', parent_workflow)
        self.assertIn('WORKFLOW "03_step_design_review/workflow.lgwf"', parent_workflow)
        self.assertIn("WRITE state.lgwf_wf_create.dsl_reference_context;", parent_workflow)
        self.assertIn('READ workspace file ".lgwf/create_reference_context/step-design-reference-index.md";', parent_workflow)
        self.assertIn('READ workspace dir ".lgwf/create_reference_context";', parent_workflow)
        self.assertIn("PY prepare_dsl_reference_context", reference_workflow)
        self.assertNotIn("PY prepare_step_design_authoring_context", proposal_workflow)
        self.assertIn("CODEX generate_step_designs", proposal_workflow)
        self.assertNotIn("CONTEXT state.lgwf_wf_create.dsl_reference_context", proposal_workflow)
        self.assertNotIn("READ state.lgwf_wf_create.dsl_reference_context;", proposal_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"', proposal_workflow)
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context"', proposal_workflow)
        self.assertIn('READ workspace file ".lgwf/create_reference_context/step-design-reference-index.md";', proposal_workflow)
        self.assertIn('READ workspace dir ".lgwf/create_reference_context";', proposal_workflow)
        self.assertIn("REACT repair_step_designs_proposal", proposal_workflow)
        self.assertIn("REASON CODEX", proposal_workflow)
        self.assertIn("ACT CODEX", proposal_workflow)
        self.assertIn("OBSERVE PY", proposal_workflow)
        self.assertIn("DECIDE PY", proposal_workflow)
        self.assertRegex(
            proposal_workflow,
            r"repair_step_designs_proposal\s+THEN\s+assert_step_designs_proposal_quality_gate",
        )
        contracts = json.loads((ROOT / "artifact_contracts.json").read_text(encoding="utf-8"))
        script_writes = contracts["script_writes"]["prepare_dsl_reference_context"]
        for relative in (
            "03_confirm_step_designs/artifact_contracts.json",
            "03_confirm_step_designs/01_reference_context/artifact_contracts.json",
            "03_confirm_step_designs/03_step_design_review/artifact_contracts.json",
        ):
            with self.subTest(artifact_contract=relative):
                local_contract = json.loads((ROOT / relative).read_text(encoding="utf-8"))
                self.assertIn("bootstrap_inputs", local_contract)
                self.assertIn("final_outputs", local_contract)

        text = proposal_workflow
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context"', text)
        self.assertIn('CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"', text)
        self.assertNotIn('CONTEXT workspace file ".lgwf/create_reference_context/index.md"', text)
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context/dsl-assist"', text)
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context/module-contract"', text)
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context/workflow-modular-development"', text)
        act_block = proposal_workflow.split('PROMPT "agents/act_step_design_repair.md"', 1)[-1]
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context"', act_block)
        self.assertNotIn('CONTEXT workspace file ".lgwf/create_reference_context/step-design-reference-index.md"', act_block)
        for _ in (0,):
            for reference in (
                ".lgwf/create_reference_context/step-design-reference-index.md",
                ".lgwf/create_reference_context/implementation-reference-index.md",
                ".lgwf/create_reference_context/dsl-assist/guide.md",
                ".lgwf/create_reference_context/dsl-assist/create-workflow.md",
                ".lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md",
                ".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md",
                ".lgwf/create_reference_context/module-contract/module-contract.md",
            ):
                self.assertIn(reference, script_writes)
        self.assertIn(
            'WRITE workspace file ".lgwf/create_reference_context/step-design-reference-index.md";',
            reference_workflow,
        )
        self.assertIn(
            'WRITE workspace file ".lgwf/create_reference_context/implementation-reference-index.md";',
            reference_workflow,
        )
        self.assertTrue(
            (ROOT / "03_confirm_step_designs/01_reference_context/resources/step_design_reference_index.md").is_file()
        )
        self.assertTrue(
            (
                ROOT
                / "03_confirm_step_designs/01_reference_context/resources/implementation_reference_index.md"
            ).is_file()
        )
        self.assertNotIn('READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";', root_workflow)
        self.assertNotIn('READ workspace dir ".lgwf/create_reference_context";', root_workflow)
        self.assertNotIn('READ workspace file ".lgwf/create_reference_context/dsl-assist/create-workflow.md";', root_workflow)
        self.assertNotIn('READ workspace file ".lgwf/create_reference_context/dsl-assist/guide.md";', root_workflow)
        self.assertNotIn(
            'READ workspace file ".lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md";',
            root_workflow,
        )
        self.assertNotIn('workspace file ".lgwf/create_reference_context/implementation-reference-index.md"', implementation_workflow)
        self.assertNotIn('workspace dir ".lgwf/create_reference_context"', implementation_workflow)
        self.assertNotIn('workspace dir ".lgwf/create_reference_context/dsl-assist"', implementation_workflow)
        self.assertNotIn(
            'workspace dir ".lgwf/create_reference_context/workflow-modular-development"',
            implementation_workflow,
        )

    def test_docs_no_longer_describe_confirmed_artifacts_as_future_only(self) -> None:
        stale_patterns = (
            "未来确认后固化接口",
            "不是当前 run 必需产物",
            "当前阶段不要求也不生成 `.lgwf/create_requirements.json`",
            "当前 run 不要求生成 `.lgwf/step_designs.json`",
        )
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for pattern in stale_patterns:
                self.assertNotIn(pattern, text, path.as_posix())

    def test_scaffold_plan_includes_generic_stage_placeholders(self) -> None:
        module = load_module(
            ROOT / "02_confirm_business_flow/03_scaffold_package/scripts/scaffold_package.py",
            "scaffold_integrity",
        )
        plan = module.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "business_flow": {"stages": []},
            }
        )
        for relative in (
            "entry_contract.json",
            "wf/artifact_contracts.json",
            "wf/01_prepare/workflow.lgwf",
            "wf/01_prepare/agents/prompt.md",
            "wf/01_prepare/scripts/run.py",
            "wf/01_prepare/resources/README.md",
        ):
            self.assertIn(relative, plan["create_files"])
        self.assertEqual(plan["stage_manifest"][0]["stage_dir"], "01_prepare")
        self.assertIn("wf/shared/scripts", plan["create_dirs"])
        self.assertNotIn("wf/common/confirmation_io.py", plan["create_files"])
        self.assertNotIn("wf/01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py", plan["create_files"])

    def test_summary_workflow_uses_py_result_and_script_writes_json(self) -> None:
        workflow = (ROOT / "06_summarize_create_result/workflow.lgwf").read_text(encoding="utf-8")
        script = (ROOT / "06_summarize_create_result/scripts/summarize_create_result.py").read_text(encoding="utf-8")
        self.assertNotIn("OUTPUT_JSON", workflow)
        self.assertIn("RESULT state.lgwf_wf_create.summary_result", workflow)
        self.assertIn("create_result_summary.json", script)

    def test_implementation_audit_observe_stays_inside_repair_before_summary_and_handoff(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        implement_workflow = (ROOT / "04_implement_steps_react/workflow.lgwf").read_text(encoding="utf-8")
        repair_workflow = (ROOT / "04_implement_steps_react/02_repair_implementation_react/workflow.lgwf").read_text(
            encoding="utf-8"
        )
        summary_workflow = (ROOT / "06_summarize_create_result/workflow.lgwf").read_text(encoding="utf-8")
        handoff_workflow = (ROOT / "07_post_fix_handoff/workflow.lgwf").read_text(encoding="utf-8")
        observe_workflow = (
            ROOT / "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertNotRegex(workflow, r"PY\s+validate_.*package")
        self.assertNotIn("created_package_" + "validation", workflow)
        self.assertNotIn("enrich_contracts_react", workflow)
        self.assertFalse((ROOT / "05_enrich_contracts_react").exists())
        self.assertIn(
            "THEN implement_draft\n"
            "  THEN implement_steps_react\n"
            "  THEN summarize_create_result",
            workflow,
        )
        self.assertIn('WORKFLOW "02_repair_implementation_react/workflow.lgwf"', implement_workflow)
        self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
        self.assertIn("PY audit_current_implementation", observe_workflow)
        self.assertIn('SCRIPT "scripts/audit_current_implementation.py"', observe_workflow)
        self.assertIn('READ workspace file ".lgwf/step_designs.json";', observe_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_audit_result.json";', observe_workflow)
        for outer_workflow in (handoff_workflow,):
            self.assertNotIn('workspace file ".lgwf/implementation_audit_result.json"', outer_workflow)
            self.assertNotIn('workspace file ".lgwf/implementation_observe.json"', outer_workflow)
            self.assertNotIn('workspace file ".lgwf/implementation_decision.json"', outer_workflow)
        for audit_boundary_workflow in (workflow, implement_workflow):
            self.assertIn('workspace file ".lgwf/implementation_audit_result.json"', audit_boundary_workflow)
            self.assertNotIn('workspace file ".lgwf/implementation_observe.json"', audit_boundary_workflow)
            self.assertNotIn('workspace file ".lgwf/implementation_decision.json"', audit_boundary_workflow)
        self.assertIn('READ workspace file ".lgwf/implementation_audit_result.json";', summary_workflow)
        self.assertNotIn('workspace file ".lgwf/implementation_observe.json"', summary_workflow)
        self.assertNotIn('workspace file ".lgwf/implementation_decision.json"', summary_workflow)

    def test_agents_doc_names_route_back_to_facade_when_out_of_scope(self) -> None:
        text = (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for workflow_id in ("wf-fix", "wf-prompt-fix", "wf-prompt-upgrade", "e2e-test-generator"):
            self.assertIn(workflow_id, text)
        self.assertIn("回到 facade 路由", text)


if __name__ == "__main__":
    unittest.main()
