from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[3]
SOURCE_WF_ROOT = PACKAGE_ROOT / "wf"
TMP_ROOT = REPO_ROOT / ".tmp"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class RuntimeMirrorPathsTest(unittest.TestCase):
    def setUp(self) -> None:
        TMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="wf-create-runtime-", dir=TMP_ROOT)
        self.work_dir = Path(self.temp_dir.name)
        self.workflow_root = self.work_dir / ".lgwf" / "workflow"
        shutil.copytree(SOURCE_WF_ROOT, self.workflow_root)
        (self.work_dir / ".lgwf").mkdir(exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, relative_script: str, stdin_payload: dict | None = None) -> dict:
        script = self.workflow_root / relative_script
        self.assertTrue(script.is_file(), relative_script)
        input_text = "" if stdin_payload is None else json.dumps(stdin_payload, ensure_ascii=False)
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=self.work_dir,
            input=input_text,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def seed_confirmed_requirements_and_business_flow(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "create_requirements.json",
            {
                "confirmed": {
                    "workflow_name": "git-diff-brief",
                    "target_package_root": "skills/git-diff-brief",
                    "package_profile": "internal_workflow_package",
                }
            },
        )
        write_json(
            self.work_dir / ".lgwf" / "business_flow.json",
            {
                "confirmed": {
                    "workflow_name": "git-diff-brief",
                    "target_package_root": "skills/git-diff-brief",
                    "package_profile": "internal_workflow_package",
                    "stages": [{"stage_id": "collect_git_context", "key_nodes": ["collect_git_context"]}],
                }
            },
        )

    def test_scaffold_package_loads_resources_and_validator_from_runtime_workflow_mirror(self) -> None:
        self.seed_confirmed_requirements_and_business_flow()

        result = self.run_script("02_confirm_business_flow/03_scaffold_package/scripts/scaffold_package.py")

        plan = result["lgwf_wf_create.scaffold_package_result"]["scaffold_plan"]
        self.assertEqual(plan["target_package_root"], "skills/git-diff-brief")
        self.assertIn("wf/workflow.lgwf", plan["create_files"])
        self.assertTrue((self.workflow_root / "shared" / "scripts" / "validate_two_layer_workflow.py").is_file())
        self.assertFalse((self.work_dir / ".lgwf" / "scripts" / "validate_two_layer_workflow.py").exists())

    def test_prepare_dsl_reference_context_writes_only_runtime_artifacts(self) -> None:
        stale_scaffold_context = self.work_dir / ".lgwf" / "create_reference_context" / "scaffold"
        stale_scaffold_context.mkdir(parents=True)
        (stale_scaffold_context / "scaffold_template_spec.md").write_text("stale", encoding="utf-8")
        stale_root_manifest = self.work_dir / ".lgwf" / "create_reference_context" / "dsl_reference_context.json"
        stale_root_manifest.parent.mkdir(parents=True, exist_ok=True)
        stale_root_manifest.write_text("stale", encoding="utf-8")
        stale_dsl_manifest = (
            self.work_dir
            / ".lgwf"
            / "create_reference_context"
            / "dsl-assist"
            / "dsl_reference_context.json"
        )
        stale_dsl_manifest.parent.mkdir(parents=True, exist_ok=True)
        stale_dsl_manifest.write_text("stale", encoding="utf-8")

        result = self.run_script("03_confirm_step_designs/01_reference_context/scripts/prepare_dsl_reference_context.py")

        context = result["lgwf_wf_create.dsl_reference_context"]
        self.assertTrue(context["reference_context_ready"])
        self.assertTrue(context["reference_index_ready"])
        self.assertTrue(context["implementation_reference_index_ready"])
        self.assertTrue(context["modular_development_context_ready"])
        self.assertTrue(context["module_contract_context_ready"])
        self.assertTrue((self.work_dir / ".lgwf" / "create_reference_context" / "dsl-assist" / "guide.md").is_file())
        self.assertFalse(
            (
                self.work_dir
                / ".lgwf"
                / "create_reference_context"
                / "dsl-assist"
                / "dsl_reference_context.json"
            ).exists()
        )
        self.assertFalse((self.work_dir / ".lgwf" / "create_reference_context" / "dsl_reference_context.json").exists())
        self.assertTrue(
            (
                self.work_dir
                / ".lgwf"
                / "create_reference_context"
                / "step-design-reference-index.md"
            ).is_file()
        )
        self.assertTrue(
            (
                self.work_dir
                / ".lgwf"
                / "create_reference_context"
                / "implementation-reference-index.md"
            ).is_file()
        )
        self.assertFalse((self.work_dir / ".lgwf" / "create_reference_context" / "index.md").exists())
        self.assertFalse((self.work_dir / ".lgwf" / "create_reference_context" / "scaffold").exists())
        self.assertTrue(
            (
                self.work_dir
                / ".lgwf"
                / "create_reference_context"
                / "workflow-modular-development"
                / "LGWF_WF_MODULAR_DEVELOPMENT.md"
            ).is_file()
        )
        self.assertTrue(
            (
                self.work_dir
                / ".lgwf"
                / "create_reference_context"
                / "module-contract"
                / "module-contract.md"
            ).is_file()
        )
        self.assertFalse((self.workflow_root / ".lgwf").exists())

    def test_prepare_dsl_reference_context_does_not_manage_step_design_markdown_drafts(self) -> None:
        stale_doc = self.work_dir / "docs" / "steps" / "old-workflow.md"
        stale_doc.parent.mkdir(parents=True)
        stale_doc.write_text("stale workflow draft", encoding="utf-8")

        result = self.run_script("03_confirm_step_designs/01_reference_context/scripts/prepare_dsl_reference_context.py")

        context = result["lgwf_wf_create.dsl_reference_context"]
        self.assertNotIn("step_design_draft_dir", context)
        self.assertTrue(stale_doc.exists())

    def test_prepare_implementation_context_resolves_target_from_repo_root_not_run_cwd(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "step_designs.json",
            {
                "confirmed": {
                    "workflow_name": "git-diff-brief",
                    "target_package_root": "skills/git-diff-brief",
                    "package_profile": "internal_workflow_package",
                }
            },
        )
        (self.work_dir / ".git").mkdir()

        result = self.run_script("03_confirm_step_designs/03_step_design_review/scripts/prepare_implementation_context.py")

        context = result["lgwf_wf_create.implementation_context"]
        self.assertEqual(context["target_package_root"], "skills/git-diff-brief")
        self.assertEqual(Path(context["workspace_root"]), self.work_dir)
        self.assertEqual(
            Path(context["target_package_abs"]),
            self.work_dir / "skills" / "git-diff-brief",
        )
        path_parts = [part.lower() for part in Path(context["target_package_abs"]).parts]
        self.assertNotIn(("plugins", "plugins"), list(zip(path_parts, path_parts[1:])))
        self.assertTrue((self.work_dir / ".lgwf" / "implementation_context.json").is_file())
        self.assertFalse((self.workflow_root / ".lgwf").exists())

    def test_prepare_implementation_context_does_not_reuse_stale_self_output(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "implementation_context.json",
            {
                "workflow_name": "stale-workflow",
                "target_package_root": "skills/stale-workflow",
                "package_profile": "skill_wrapped_workflow",
            },
        )
        write_json(
            self.work_dir / ".lgwf" / "step_designs.json",
            {
                "confirmed": {
                    "workflow_name": "git-diff-brief",
                    "target_package_root": "skills/git-diff-brief",
                    "package_profile": "internal_workflow_package",
                }
            },
        )
        (self.work_dir / ".git").mkdir()

        result = self.run_script("03_confirm_step_designs/03_step_design_review/scripts/prepare_implementation_context.py")

        context = result["lgwf_wf_create.implementation_context"]
        self.assertEqual(context["workflow_name"], "git-diff-brief")
        self.assertEqual(context["target_package_root"], "skills/git-diff-brief")
        self.assertEqual(context["package_profile"], "internal_workflow_package")

    def test_summarize_create_result_uses_current_target_package_from_stdin(self) -> None:
        payload = {
            "workflow_name": "git-diff-brief",
            "target_package_root": "skills/git-diff-brief",
            "produced_files": ["wf/workflow.lgwf", "AGENTS.md"],
        }

        result = self.run_script("06_summarize_create_result/scripts/summarize_create_result.py", payload)

        self.assertEqual(result["target_package_root"], "skills/git-diff-brief")
        self.assertTrue((self.work_dir / ".lgwf" / "create_result_summary.json").is_file())
        self.assertTrue((self.work_dir / "reports" / "create-workflow" / "create_result_report.md").is_file())
        self.assertFalse((self.workflow_root / "reports").exists())

    def test_summarize_create_result_falls_back_to_implementation_result_when_stdin_empty(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "implementation_result.json",
            {
                "workflow_name": "git-diff-brief",
                "target_package_root": "skills/git-diff-brief",
                "generated": {"root_files": ["skills/git-diff-brief/AGENTS.md"]},
                "verification": [
                    {
                        "command": "python -m unittest discover skills\\git-diff-brief\\tests",
                        "result": "passed",
                    }
                ],
            },
        )

        result = self.run_script("06_summarize_create_result/scripts/summarize_create_result.py")

        self.assertEqual(result["workflow_name"], "git-diff-brief")
        self.assertEqual(result["target_package_root"], "skills/git-diff-brief")
        self.assertEqual(
            result["validation"]["minimal_command"],
            "python -m unittest discover skills\\git-diff-brief\\tests",
        )
        report = (self.work_dir / "reports" / "create-workflow" / "create_result_report.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("# git-diff-brief 结果汇总", report)

    def test_summarize_create_result_uses_top_level_generated_files_and_audit_status(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "implementation_result.json",
            {
                "workflow_name": "git-diff-brief",
                "target_package_root": "skills/git-diff-brief",
                "status": "failed",
                "generated_files": [{"path": "skills/git-diff-brief/wf/workflow.lgwf"}],
                "failed_units": ["root_workflow"],
            },
        )
        write_json(
            self.work_dir / ".lgwf" / "implementation_audit_result.json",
            {
                "passed": False,
                "status": "failed",
                "needs_post_fix": False,
                "failures": ["root workflow failed"],
            },
        )

        result = self.run_script("06_summarize_create_result/scripts/summarize_create_result.py")

        self.assertEqual(result["status"], "draft_needs_implementation_repair")
        self.assertEqual(result["produced_files"], ["wf/workflow.lgwf"])
        self.assertEqual(result["implementation_audit"]["failures"], ["root workflow failed"])


if __name__ == "__main__":
    unittest.main()
