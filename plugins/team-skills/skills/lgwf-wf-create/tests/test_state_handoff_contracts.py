from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from contextlib import redirect_stdout
from io import StringIO
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
        self.assertIn('STEP define_requirements\n  WORKFLOW "02_confirm_requirements/workflow.lgwf"', main_workflow)
        self.assertIn('STEP design_structure\n  WORKFLOW "04_confirm_business_flow/workflow.lgwf"', main_workflow)
        self.assertIn('STEP implement_draft\n  WORKFLOW "07_confirm_step_designs/workflow.lgwf"', main_workflow)
        self.assertNotIn("PY prepare_requirements_confirmation", main_workflow)
        self.assertNotIn("APPROVAL confirm_requirements", main_workflow)

        for workflow_relative, node in (
            ("02_confirm_requirements/workflow.lgwf", "prepare_requirements_confirmation"),
            ("04_confirm_business_flow/workflow.lgwf", "prepare_business_flow_confirmation"),
            ("07_confirm_step_designs/workflow.lgwf", "prepare_step_design_confirmation"),
        ):
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            self.assertIn(f"PY {node}", workflow)
            self.assertIn(f"RESULT state.lgwf_wf_create.{node}_result", workflow)
            self.assertIn("UPDATES_STATE", workflow)
            self.assertRegex(workflow, rf"THEN {node}\s+THEN confirm_")

    def test_confirmation_context_scripts_emit_expected_state_keys(self) -> None:
        cases = (
            (
                "02_confirm_requirements/scripts/prepare_requirements_confirmation.py",
                "create_requirements_proposal.json",
                {"workflow_name": "demo", "target_package_root": "plugins/team-skills/skills/demo"},
                "lgwf_wf_create.requirements_confirmation_context",
            ),
            (
                "04_confirm_business_flow/scripts/prepare_business_flow_confirmation.py",
                "business_flow_proposal.json",
                {"workflow_name": "demo", "stages": []},
                "lgwf_wf_create.business_flow_confirmation_context",
            ),
            (
                "07_confirm_step_designs/scripts/prepare_step_design_confirmation.py",
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
                self.assertEqual(data[state_key]["proposal"], proposal)

    def test_revision_context_scripts_emit_revision_request_and_state_keys(self) -> None:
        cases = (
            (
                "02_confirm_requirements/scripts/prepare_requirements_revision_confirmation.py",
                "create_requirements_proposal.json",
                "create_requirements_approval.json",
                {"workflow_name": "demo"},
                "lgwf_wf_create.requirements_revision_context",
            ),
            (
                "04_confirm_business_flow/scripts/prepare_business_flow_revision_confirmation.py",
                "business_flow_proposal.json",
                "business_flow_approval.json",
                {"stages": []},
                "lgwf_wf_create.business_flow_revision_context",
            ),
            (
                "07_confirm_step_designs/scripts/prepare_step_design_revision_confirmation.py",
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
                self.assertEqual(data[state_key]["proposal"], proposal)
                self.assertEqual(data[state_key]["revision_request"]["decision"], "revise")

    def test_scaffold_script_can_build_plan_from_confirmed_runtime_artifacts(self) -> None:
        module = load_module(
            ROOT / "04_confirm_business_flow/05_scaffold_package/scripts/scaffold_package.py",
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
                            "target_package_root": "plugins/team-skills/skills/demo",
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
            self.assertEqual(plan["target_package_root"], "plugins/team-skills/skills/demo")
            self.assertEqual(plan["derived_from_business_flow"][0]["stage_id"], "package_scaffold")

    def test_scaffold_script_has_safe_default_without_confirmed_artifacts(self) -> None:
        module = load_module(
            ROOT / "04_confirm_business_flow/05_scaffold_package/scripts/scaffold_package.py",
            "scaffold_default",
        )
        with tempfile.TemporaryDirectory() as temp:
            plan = module.build_scaffold_plan_from_root(Path(temp))
            self.assertEqual(plan["workflow_name"], "lgwf-wf-create-example")
            self.assertEqual(plan["target_package_root"], "plugins/team-skills/skills/example-workflow")

    def test_confirmation_decision_accepts_lgwf_value_wrappers(self) -> None:
        helper = load_module(ROOT / "common/confirmation_io.py", "confirmation_io_contract")
        for approval in (
            {"decision": "approve"},
            {"decision": {"value": "approve"}},
            {"decision": {"decision": "approve"}},
        ):
            helper.require_approve(approval)
        with self.assertRaises(ValueError):
            helper.require_approve({"decision": {"value": "revise"}})

    def test_summary_rejects_invalid_runtime_artifact_paths(self) -> None:
        summary = load_module(ROOT / "09_summarize_create_result/scripts/summarize_create_result.py", "summary_handoff")
        with self.assertRaises(ValueError):
            summary.build_summary({"runtime_artifacts": ["workflow.lgwf"]})
        with self.assertRaises(ValueError):
            summary.build_summary({"runtime_artifacts": [".lgwf/../bad.json"]})

    def test_scaffold_plan_lists_confirmation_context_scripts(self) -> None:
        scaffold = load_module(
            ROOT / "04_confirm_business_flow/05_scaffold_package/scripts/scaffold_package.py",
            "scaffold_files",
        )
        plan = scaffold.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "plugins/team-skills/skills/demo",
                "business_flow": {"stages": []},
            }
        )
        for relative in (
            "wf/02_confirm_requirements/scripts/prepare_requirements_confirmation.py",
            "wf/02_confirm_requirements/scripts/prepare_requirements_revision_confirmation.py",
            "wf/04_confirm_business_flow/scripts/prepare_business_flow_confirmation.py",
            "wf/04_confirm_business_flow/scripts/prepare_business_flow_revision_confirmation.py",
            "wf/07_confirm_step_designs/scripts/prepare_step_design_confirmation.py",
            "wf/07_confirm_step_designs/scripts/prepare_step_design_revision_confirmation.py",
        ):
            self.assertIn(relative, plan["create_files"])

    def test_prompt_docs_mention_confirmation_context_handoff(self) -> None:
        expectations = (
            ("02_confirm_requirements/01_propose_requirements_react/agents/act.md", "requirements_confirmation_context"),
            ("04_confirm_business_flow/03_propose_business_flow_react/agents/act.md", "business_flow_confirmation_context"),
            ("07_confirm_step_designs/06_design_steps_react/agents/act.md", "step_design_confirmation_context"),
        )
        for relative, state_key in expectations:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(state_key, text)

    def test_apply_scripts_return_output_artifact_path(self) -> None:
        for relative, approval_name, output_name in (
            ("02_confirm_requirements/scripts/apply_confirmed_requirements.py", "create_requirements_approval.json", "create_requirements.json"),
            ("04_confirm_business_flow/scripts/apply_confirmed_business_flow.py", "business_flow_approval.json", "business_flow.json"),
            ("07_confirm_step_designs/scripts/apply_confirmed_step_designs.py", "step_design_confirmation_record.json", "step_designs.json"),
        ):
            module = load_module(ROOT / relative, relative.replace("/", "_return_path"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / approval_name).write_text(json.dumps({"decision": "approve"}), encoding="utf-8")
                result = module.write_confirmed_artifact(root)
                self.assertIn("artifact_path", next(iter(result.values())))
                self.assertEqual(next(iter(result.values()))["artifact_path"], f".lgwf/{output_name}")

    def test_summary_report_path_is_relative(self) -> None:
        summary = load_module(ROOT / "09_summarize_create_result/scripts/summarize_create_result.py", "summary_report_path")
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
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
