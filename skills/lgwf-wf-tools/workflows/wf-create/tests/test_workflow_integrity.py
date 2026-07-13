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
            "01_raw_intent/resources/raw_intent_contract.md",
            "01_raw_intent/scripts/prepare_confirmation.py",
            "01_raw_intent/scripts/apply_confirmed.py",
            "02_requirements_proposal/workflow.lgwf",
            "02_requirements_proposal/README.md",
            "02_requirements_proposal/agents/propose_requirements.md",
            "02_requirements_proposal/agents/spec.md",
            "02_requirements_proposal/scripts/validate_proposal.py",
            "02_requirements_proposal/resources/proposal_schema.json",
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
            "agents/propose_requirements_react.md",
            "agents/propose_requirements_react_spec.md",
            "resources/raw_intent_contract.md",
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
                "CODEX propose_requirements_react",
                "PY validate_requirements_proposal",
                'PROMPT "agents/propose_requirements.md"',
                'CONTEXT workflow file "agents/spec.md"',
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
                "02_confirm_business_flow/workflow.lgwf",
                "confirm_business_flow",
                "prepare_business_flow_revision_confirmation",
                "apply_confirmed_business_flow",
                ".lgwf/business_flow_approval.json",
            ),
            (
                "03_confirm_step_designs/workflow.lgwf",
                "confirm_step_designs",
                "prepare_step_design_revision_confirmation",
                "apply_confirmed_step_designs",
                ".lgwf/step_design_confirmation_record.json",
            ),
        )
        for relative, approval, prepare_revision, apply_node, persist in expectations:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(f"REVIEW {approval}", text)
            self.assertIn('OPTIONS ["approve", "revise", "reject"]', text)
            self.assertIn(f'PERSIST "{persist}"', text)
            self.assertIn(f"PY {prepare_revision}", text)
            self.assertIn("FLOW {", text)
            self.assertIn(approval, text)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', text)
            self.assertIn(f'WHEN "revise" THEN {prepare_revision}', text)
            self.assertIn(f"{prepare_revision}\n  THEN {approval}", text)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', text)
            self.assertIn('WHEN "reject" THEN FAIL_ALL', text)

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
            ("02_confirm_business_flow/scripts/apply_confirmed_business_flow.py", "business_flow_approval.json", "business_flow.json"),
            ("03_confirm_step_designs/scripts/apply_confirmed_step_designs.py", "step_design_confirmation_record.json", "step_designs.json"),
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

    def test_apply_scripts_use_fixed_proposal_after_approved_revision(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
                "create_requirements_approval.json",
                "create_requirements_revision_approval.json",
                "create_requirements_proposal.json",
                "create_requirements.json",
                {"workflow_name": "demo", "target_package_root": "skills/demo"},
            ),
            (
                "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
                "business_flow_approval.json",
                "business_flow_revision_approval.json",
                "business_flow_proposal.json",
                "business_flow.json",
                {"workflow_name": "demo", "stages": [{"stage_id": "scaffold"}]},
            ),
            (
                "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_design_revision_approval.json",
                "step_designs_proposal.json",
                "step_designs.json",
                {"step_designs": [{"step_slug": "scaffold"}]},
            ),
        )
        for relative, approval_name, revision_name, proposal_name, output_name, confirmed in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_revision"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / proposal_name).write_text(json.dumps(confirmed), encoding="utf-8")
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"decision": "revise", "changes": ["local change"]}),
                    encoding="utf-8",
                )
                (lgwf_dir / revision_name).write_text(
                    json.dumps(
                        {
                            "decision": "approve",
                            "confirmed": {"approval": "approve", "route": "approve"},
                        }
                    ),
                    encoding="utf-8",
                )
                result = module.write_confirmed_artifact(root)
                artifact = next(value for value in result.values() if isinstance(value, dict) and "artifact_path" in value)
                self.assertEqual(artifact["artifact_path"], f".lgwf/{output_name}")
                self.assertEqual(artifact["source_approval_file"], f".lgwf/{revision_name}")
                self.assertEqual(artifact["confirmed"], confirmed)
                self.assertNotIn("approval", artifact)

    def test_apply_scripts_reject_missing_fixed_proposal(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
                "create_requirements_approval.json",
                "create_requirements_revision_approval.json",
                "create_requirements.json",
            ),
            (
                "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
                "business_flow_approval.json",
                "business_flow_revision_approval.json",
                "business_flow.json",
            ),
            (
                "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_design_revision_approval.json",
                "step_designs.json",
            ),
        )
        for relative, approval_name, revision_name, output_name in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_approval_field"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"approval": "revise", "changes": ["local change"]}),
                    encoding="utf-8",
                )
                (lgwf_dir / revision_name).write_text(
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
        self.assertNotIn(".lgwf/create_requirements.json", summary["produced_files"])

    def test_apply_scripts_share_common_confirmation_helpers(self) -> None:
        for relative in (
            "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
            "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
            "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("from confirmation_io import", text)
            self.assertIn("shared", text)

    def test_step_design_and_implementation_use_dsl_assist_context(self) -> None:
        parent_workflow = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY prepare_dsl_reference_context", parent_workflow)
        self.assertIn("prepare_dsl_reference_context THEN design_steps_react", parent_workflow)
        contracts = json.loads((ROOT / "artifact_contracts.json").read_text(encoding="utf-8"))
        script_writes = contracts["script_writes"]["prepare_dsl_reference_context"]

        text = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context/dsl-assist"', text)
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context/workflow-modular-development"', text)
        for _ in (0,):
            for reference in (
                ".lgwf/create_reference_context/dsl-assist/guide.md",
                ".lgwf/create_reference_context/dsl-assist/create-workflow.md",
                ".lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md",
                ".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md",
                ".lgwf/create_reference_context/module-contract/module-contract.md",
            ):
                self.assertIn(reference, script_writes)

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
            ROOT / "02_confirm_business_flow/scripts/scaffold_package.py",
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

    def test_implementation_observe_audit_runs_before_summary_and_handoff(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        implement_workflow = (ROOT / "04_implement_steps_react/workflow.lgwf").read_text(encoding="utf-8")
        observe_workflow = (ROOT / "04_implement_steps_react/observe_audit.lgwf").read_text(encoding="utf-8")
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
        self.assertIn("OBSERVE WORKFLOW observe_audit", implement_workflow)
        self.assertIn("PY audit_created_package", observe_workflow)
        self.assertIn('SCRIPT "scripts/audit_created_package.py"', observe_workflow)
        self.assertIn('READ workspace file ".lgwf/step_designs.json";', observe_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_audit_result.json";', observe_workflow)

    def test_agents_doc_names_route_back_to_facade_when_out_of_scope(self) -> None:
        text = (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for workflow_id in ("wf-fix", "wf-prompt-fix", "wf-prompt-upgrade", "e2e-test-generator"):
            self.assertIn(workflow_id, text)
        self.assertIn("回到 facade 路由", text)


if __name__ == "__main__":
    unittest.main()
