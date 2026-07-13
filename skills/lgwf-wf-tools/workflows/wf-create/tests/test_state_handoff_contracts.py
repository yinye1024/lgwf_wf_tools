from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROOT = PACKAGE_ROOT / "wf"
POST_FIX_HANDOFF_ROOT = ROOT / "07_post_fix_handoff"
POST_FIX_HANDOFF_SCRIPT = POST_FIX_HANDOFF_ROOT / "scripts" / "prepare_post_fix_handoff.py"
sys.dont_write_bytecode = True


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class pushd:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous = Path.cwd()

    def __enter__(self) -> None:
        import os

        os.chdir(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        import os

        os.chdir(self.previous)


class StateHandoffContractTest(unittest.TestCase):
    def test_confirmation_context_prepare_nodes_are_owned_by_gate_workflows(self) -> None:
        main_workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('STEP define_requirements\n  WORKFLOW "01_confirm_requirements/workflow.lgwf"', main_workflow)
        self.assertIn('STEP design_structure\n  WORKFLOW "02_confirm_business_flow/workflow.lgwf"', main_workflow)
        self.assertIn('STEP implement_draft\n  WORKFLOW "03_confirm_step_designs/workflow.lgwf"', main_workflow)
        self.assertNotIn("PY prepare_requirements_confirmation", main_workflow)
        self.assertNotIn("APPROVAL confirm_requirements", main_workflow)

        for workflow_relative, node in (
            ("01_confirm_requirements/03_requirements_review/workflow.lgwf", "prepare_requirements_confirmation"),
            ("02_confirm_business_flow/02_business_flow_review/workflow.lgwf", "prepare_business_flow_confirmation"),
            ("03_confirm_step_designs/03_step_design_review/workflow.lgwf", "prepare_step_design_confirmation"),
        ):
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            self.assertIn(f"PY {node}", workflow)
            self.assertIn(f"RESULT state.lgwf_wf_create.{node}_result", workflow)
            self.assertIn("UPDATES_STATE", workflow)
            self.assertRegex(workflow, rf"{node}\s+THEN confirm_")

    def test_confirmation_context_scripts_emit_expected_state_keys(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/prepare_confirmation.py",
                "create_requirements_proposal.json",
                {"workflow_name": "demo", "target_package_root": "skills/demo"},
                "lgwf_wf_create.requirements_confirmation_context",
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/scripts/prepare_confirmation.py",
                "business_flow_proposal.json",
                {"workflow_name": "demo", "stages": []},
                "lgwf_wf_create.business_flow_confirmation_context",
            ),
            (
                "03_confirm_step_designs/03_step_design_review/scripts/prepare_step_design_confirmation.py",
                "step_designs_proposal.json",
                {"step_designs": [{"step_slug": "demo"}]},
                "lgwf_wf_create.step_design_confirmation_context",
            ),
        )
        for relative, proposal_name, proposal, state_key in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / proposal_name).write_text(json.dumps(proposal), encoding="utf-8")
                output = StringIO()
                with pushd(root), redirect_stdout(output):
                    module.main()
                data = json.loads(output.getvalue())
                self.assertIn(state_key, data)
                context = data[state_key]
                self.assertEqual(context["proposal"], proposal)
                self.assertEqual(context["allowed_decisions"], ["approve", "revise", "reject"])
                self.assertIsInstance(context["review_context_json"], dict)
                self.assertEqual(context["review_context_json"]["proposal"], proposal)
                self.assertEqual(context["review_context_json"]["allowed_decisions"], ["approve", "revise", "reject"])
                self.assertEqual(context["review_reentry_node"], context["review_context_json"]["review_node"])
                self.assertIn("完整 JSON", context["revise_instruction"])
                self.assertIn("review_context_json", context["display_template"])

    def test_revision_context_scripts_emit_revision_request_and_state_keys(self) -> None:
        cases = (
            (
                "01_confirm_requirements/03_requirements_review/scripts/prepare_revision_confirmation.py",
                "create_requirements_proposal.json",
                "create_requirements_approval.json",
                {"workflow_name": "demo"},
                "lgwf_wf_create.requirements_revision_context",
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/scripts/prepare_revision_confirmation.py",
                "business_flow_proposal.json",
                "business_flow_approval.json",
                {"stages": []},
                "lgwf_wf_create.business_flow_revision_context",
            ),
            (
                "03_confirm_step_designs/03_step_design_review/scripts/prepare_step_design_revision_confirmation.py",
                "step_designs_proposal.json",
                "step_design_confirmation_record.json",
                {"step_designs": []},
                "lgwf_wf_create.step_design_revision_context",
            ),
        )
        for relative, proposal_name, approval_name, proposal, state_key in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_revision_context"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / proposal_name).write_text(json.dumps(proposal), encoding="utf-8")
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"decision": "revise", "changes": ["adjust scope"]}),
                    encoding="utf-8",
                )
                output = StringIO()
                with pushd(root), redirect_stdout(output):
                    module.main()
                data = json.loads(output.getvalue())
                self.assertIn(state_key, data)
                context = data[state_key]
                self.assertEqual(context["proposal"], proposal)
                self.assertEqual(context["revision_request"]["decision"], "revise")
                self.assertEqual(context["allowed_decisions"], ["approve", "revise", "reject"])
                self.assertIsInstance(context["review_context_json"], dict)
                self.assertEqual(context["review_context_json"]["proposal"], proposal)
                self.assertEqual(context["review_context_json"]["revision_request"]["decision"], "revise")
                self.assertIn("完整 JSON", context["instruction"])
                self.assertIn("review_context_json", context["display_template"])

    def test_scaffold_script_can_build_plan_from_confirmed_runtime_artifacts(self) -> None:
        module = load_module(
            ROOT / "02_confirm_business_flow/03_scaffold_package/scripts/scaffold_package.py",
            "scaffold_handoff",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "create_requirements.json").write_text(
                json.dumps(
                    {
                        "confirmed": {
                            "workflow_name": "demo",
                            "target_package_root": "skills/demo",
                        }
                    }
                ),
                encoding="utf-8",
            )
            (lgwf_dir / "business_flow.json").write_text(
                json.dumps({"confirmed": {"stages": [{"stage_id": "package_scaffold"}]}}),
                encoding="utf-8",
            )
            plan = module.build_scaffold_plan_from_root(root)
            self.assertEqual(plan["workflow_name"], "demo")
            self.assertEqual(plan["target_package_root"], "skills/demo")
            self.assertEqual(plan["derived_from_business_flow"][0]["stage_id"], "package_scaffold")

    def test_scaffold_script_has_safe_default_without_confirmed_artifacts(self) -> None:
        module = load_module(
            ROOT / "02_confirm_business_flow/03_scaffold_package/scripts/scaffold_package.py",
            "scaffold_default",
        )
        with tempfile.TemporaryDirectory() as temp:
            plan = module.build_scaffold_plan_from_root(Path(temp))
            self.assertEqual(plan["workflow_name"], "lgwf-wf-create-example")
            self.assertEqual(plan["target_package_root"], "skills/example-workflow")

    def test_confirmation_decision_accepts_lgwf_value_wrappers(self) -> None:
        helper = load_module(ROOT / "shared/scripts/confirmation_io.py", "confirmation_io_contract")
        for approval in (
            {"decision": "approve"},
            {"decision": {"value": "approve"}},
            {"decision": {"decision": "approve"}},
        ):
            helper.require_approve(approval)
        with self.assertRaises(ValueError):
            helper.require_approve({"decision": {"value": "revise"}})

    def test_unwrap_approval_treats_null_value_as_absent(self) -> None:
        helper = load_module(ROOT / "shared/scripts/confirmation_io.py", "confirmation_io_null_value")

        approval = helper.unwrap_approval(
            {
                "approval": "approve",
                "decision": "approve",
                "comment": "confirmed",
                "value": None,
            },
            "create_requirements_approval",
        )

        self.assertEqual(approval["approval"], "approve")
        self.assertEqual(approval["decision"], "approve")

    def test_summary_rejects_invalid_runtime_artifact_paths(self) -> None:
        summary = load_module(ROOT / "06_summarize_create_result/scripts/summarize_create_result.py", "summary_handoff")
        with self.assertRaises(ValueError):
            summary.build_summary({"runtime_artifacts": ["workflow.lgwf"]})
        with self.assertRaises(ValueError):
            summary.build_summary({"runtime_artifacts": [".lgwf/../bad.json"]})

    def test_post_fix_handoff_payload_targets_created_workflow(self) -> None:
        module = load_module(POST_FIX_HANDOFF_SCRIPT, "prepare_post_fix_handoff")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = module.build_handoff_payload(
                {
                    "target_package_root": "skills/example-workflow",
                    "workflow_name": "example-workflow",
                    "report_path": "reports/create-workflow/create_result_report.md",
                },
                root,
            )

        self.assertEqual(payload["workflow_id"], "wf-post-fix")
        self.assertEqual(payload["next_workflow_id"], "wf-post-fix")
        self.assertFalse(payload["auto_execute"])
        self.assertTrue(payload["requires_user_confirmation"])
        self.assertEqual(payload["workflow_lgwf"], "skills/lgwf-wf-tools/workflows/wf-post-fix/wf/workflow.lgwf")
        self.assertEqual(payload["work_dir"], "skills/lgwf-wf-tools/workflows/wf-post-fix/ws")
        self.assertEqual(
            payload["payload"]["post_fix_target"]["target_workflow_lgwf"],
            "skills/example-workflow/wf/workflow.lgwf",
        )
        self.assertEqual(payload["payload"]["post_fix_target"]["target_package_root"], "skills/example-workflow")
        self.assertEqual(payload["payload"]["post_fix_target"]["target_dirs"], ["skills/example-workflow"])
        self.assertIn("wf-post-fix", payload["suggested_command"])
        self.assertNotIn("diagnostic_artifacts", payload)
        self.assertNotIn("source_create_audit", payload)

    def test_post_fix_handoff_unwraps_summary_state_payload(self) -> None:
        module = load_module(POST_FIX_HANDOFF_SCRIPT, "prepare_post_fix_handoff_state_wrapper")
        summary = {
            "workflow_name": "example-workflow",
            "target_package_root": "skills/example-workflow",
        }
        self.assertEqual(module.unwrap_summary_payload({"lgwf_wf_create.summary_result": summary}), summary)
        self.assertEqual(module.unwrap_summary_payload({"summary_result": summary}), summary)

    def test_post_fix_handoff_falls_back_to_summary_file_when_stdin_state_is_empty(self) -> None:
        module = load_module(POST_FIX_HANDOFF_SCRIPT, "prepare_post_fix_handoff_file_fallback")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "create_result_summary.json").write_text(
                json.dumps(
                    {
                        "workflow_name": "example-workflow",
                        "target_package_root": "skills/example-workflow",
                        "report_path": "reports/create-workflow/create_result_report.md",
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()
            with pushd(root), patch("sys.stdin", StringIO("{}")), redirect_stdout(output):
                module.main()

            data = json.loads(output.getvalue())
            payload = data["lgwf_wf_create.post_fix_handoff_payload"]
            self.assertEqual(
                payload["payload"]["post_fix_target"]["target_workflow_lgwf"],
                "skills/example-workflow/wf/workflow.lgwf",
            )
            self.assertEqual(payload["payload"]["post_fix_target"]["target_package_root"], "skills/example-workflow")
            self.assertTrue((lgwf_dir / "post_fix_handoff_input.json").is_file())

    def test_root_workflow_ends_with_post_fix_handoff(self) -> None:
        workflow_text = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        post_fix_workflow = (POST_FIX_HANDOFF_ROOT / "workflow.lgwf").read_text(encoding="utf-8")

        self.assertIn('STEP post_fix_handoff\n  WORKFLOW "07_post_fix_handoff/workflow.lgwf"', workflow_text)
        self.assertNotIn("PY prepare_post_fix_handoff", workflow_text)
        self.assertIn("THEN summarize_create_result\n  THEN post_fix_handoff", workflow_text)
        self.assertNotIn('workspace file ".lgwf/implementation_audit_result.json"', workflow_text)
        self.assertNotIn('workspace file ".lgwf/implementation_observe.json"', workflow_text)
        self.assertNotIn('workspace file ".lgwf/implementation_decision.json"', workflow_text)

        self.assertIn("PY prepare_post_fix_handoff", post_fix_workflow)
        self.assertIn('SCRIPT "scripts/prepare_post_fix_handoff.py"', post_fix_workflow)
        self.assertIn("INPUT state.lgwf_wf_create.summary_result", post_fix_workflow)
        self.assertIn("RESULT state.lgwf_wf_create.post_fix_handoff_payload", post_fix_workflow)
        self.assertIn("HANDOFF handoff_wf_post_fix", post_fix_workflow)
        self.assertIn("CONTEXT state.lgwf_wf_create.post_fix_handoff_payload", post_fix_workflow)
        self.assertIn('PROMPT "handoff_wf_post_fix.md"', post_fix_workflow)
        self.assertIn("RESULT state.lgwf_wf_create.post_fix_handoff", post_fix_workflow)
        self.assertIn("THEN handoff_wf_post_fix", post_fix_workflow)
        self.assertNotIn('workspace file ".lgwf/implementation_audit_result.json"', post_fix_workflow)
        self.assertNotIn('workspace file ".lgwf/implementation_observe.json"', post_fix_workflow)

    def test_scaffold_plan_lists_generic_skeleton_files(self) -> None:
        scaffold = load_module(
            ROOT / "02_confirm_business_flow/03_scaffold_package/scripts/scaffold_package.py",
            "scaffold_files",
        )
        plan = scaffold.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "business_flow": {"stages": []},
            }
        )
        for relative in (
            "AGENTS.md",
            "README.md",
            "entry_contract.json",
            "wf/artifact_contracts.json",
            "wf/workflow.lgwf",
            "wf/01_prepare/workflow.lgwf",
            "wf/01_prepare/agents/prompt.md",
            "wf/01_prepare/scripts/run.py",
            "wf/01_prepare/resources/README.md",
            "tests/test_workflow_structure.py",
        ):
            self.assertIn(relative, plan["create_files"])
        self.assertIn("wf/shared/scripts", plan["create_dirs"])
        self.assertNotIn("wf/01_confirm_requirements/03_requirements_review/scripts/prepare_confirmation.py", plan["create_files"])

    def test_prompt_docs_mention_confirmation_context_handoff(self) -> None:
        expectations = (
            ("01_confirm_requirements/02_requirements_proposal/agents/propose_requirements.md", "requirements_confirmation_context"),
            ("02_confirm_business_flow/01_business_flow_proposal/agents/propose_business_flow.md", "business_flow_confirmation_context"),
            (
                "03_confirm_step_designs/02_step_design_proposal/02_act_step_designs/agents/act_step_designs.md",
                "step_design_confirmation_context",
            ),
        )
        for relative, state_key in expectations:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(state_key, text)

    def test_apply_scripts_return_output_artifact_path(self) -> None:
        for relative, approval_name, proposal_name, output_name, proposal in (
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
                {"workflow_name": "demo", "stages": []},
            ),
            (
                "03_confirm_step_designs/03_step_design_review/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_designs_proposal.json",
                "step_designs.json",
                {"step_designs": []},
            ),
        ):
            module = load_module(ROOT / relative, relative.replace("/", "_return_path"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / proposal_name).write_text(json.dumps(proposal), encoding="utf-8")
                (lgwf_dir / approval_name).write_text(json.dumps({"decision": "approve"}), encoding="utf-8")
                result = module.write_confirmed_artifact(root)
                artifacts = [value for value in result.values() if isinstance(value, dict) and "artifact_path" in value]
                self.assertTrue(artifacts)
                self.assertEqual(artifacts[0]["artifact_path"], f".lgwf/{output_name}")

    def test_apply_scripts_use_proposal_when_approval_only_records_decision(self) -> None:
        for relative, approval_name, proposal_name, expected_key in (
            (
                "01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py",
                "create_requirements_approval.json",
                "create_requirements_proposal.json",
                "workflow_name",
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/scripts/apply_confirmed.py",
                "business_flow_approval.json",
                "business_flow_proposal.json",
                "stages",
            ),
            (
                "03_confirm_step_designs/03_step_design_review/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_designs_proposal.json",
                "step_designs",
            ),
        ):
            module = load_module(ROOT / relative, relative.replace("/", "_proposal_fallback"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                proposal = {"workflow_name": "demo", "target_package_root": "skills/demo"}
                if expected_key == "stages":
                    proposal["stages"] = [{"stage_id": "collect"}]
                if expected_key == "step_designs":
                    proposal["step_designs"] = [{"stage_id": "collect", "steps": []}]
                (lgwf_dir / proposal_name).write_text(json.dumps(proposal), encoding="utf-8")
                (lgwf_dir / approval_name).write_text(
                    json.dumps(
                        {
                            "approval": "approve",
                            "decision": "approve",
                            "route": "approve",
                            "changes": [],
                            "comment": "确认通过",
                        }
                    ),
                    encoding="utf-8",
                )
                result = module.write_confirmed_artifact(root)
                artifact = next(value for value in result.values() if isinstance(value, dict) and "artifact_path" in value)
                self.assertEqual(artifact["confirmed"][expected_key], proposal[expected_key])
                self.assertNotIn("approval", artifact)

    def test_summary_report_path_is_relative(self) -> None:
        summary = load_module(ROOT / "06_summarize_create_result/scripts/summarize_create_result.py", "summary_report_path")
        with tempfile.TemporaryDirectory() as temp:
            report = summary.write_report(Path(temp), summary.build_summary({}))
            self.assertFalse(Path(report.as_posix()).is_absolute())
            self.assertEqual(report.as_posix(), "reports/create-workflow/create_result_report.md")

    def test_agents_doc_documents_state_handoff_scripts(self) -> None:
        text = (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for phrase in (
            "prepare_requirements_confirmation",
            "prepare_business_flow_confirmation",
            "prepare_step_design_confirmation",
            "revise",
            "approve`、`revise`、`reject",
            "完整 JSON",
            "重新进入同一个 REVIEW 节点",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
