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

        result = self.run_script("02_confirm_business_flow/scripts/scaffold_package.py")

        plan = result["lgwf_wf_create.scaffold_package_result"]["scaffold_plan"]
        self.assertEqual(plan["target_package_root"], "skills/git-diff-brief")
        self.assertIn("wf/workflow.lgwf", plan["create_files"])
        self.assertTrue((self.workflow_root / "shared" / "scripts" / "validate_two_layer_workflow.py").is_file())
        self.assertFalse((self.work_dir / ".lgwf" / "scripts" / "validate_two_layer_workflow.py").exists())

    def test_prepare_dsl_reference_context_writes_only_runtime_artifacts(self) -> None:
        result = self.run_script("03_confirm_step_designs/scripts/prepare_dsl_reference_context.py")

        context = result["lgwf_wf_create.dsl_reference_context"]
        self.assertTrue(context["reference_context_ready"])
        self.assertTrue((self.work_dir / ".lgwf" / "create_reference_context" / "dsl-assist" / "guide.md").is_file())
        self.assertTrue((self.work_dir / ".lgwf" / "create_reference_context" / "dsl_reference_context.json").is_file())
        self.assertFalse((self.workflow_root / ".lgwf").exists())

    def test_prepare_implementation_context_resolves_target_from_repo_root_not_run_cwd(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "scaffold_package_result.json",
            {
                "scaffold_plan": {
                    "workflow_name": "git-diff-brief",
                    "target_package_root": "skills/git-diff-brief",
                    "package_profile": "internal_workflow_package",
                }
            },
        )
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
        (self.work_dir / ".git").mkdir()

        result = self.run_script("03_confirm_step_designs/scripts/prepare_implementation_context.py")

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

    def test_summarize_create_result_uses_current_target_package_from_stdin(self) -> None:
        payload = {
            "workflow_name": "git-diff-brief",
            "target_package_root": "skills/git-diff-brief",
            "produced_files": ["wf/workflow.lgwf", "AGENTS.md"],
        }

        result = self.run_script("05_summarize_create_result/scripts/summarize_create_result.py", payload)

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

        result = self.run_script("05_summarize_create_result/scripts/summarize_create_result.py")

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


if __name__ == "__main__":
    unittest.main()
