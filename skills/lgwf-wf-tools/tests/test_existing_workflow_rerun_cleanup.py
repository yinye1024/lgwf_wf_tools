from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


FACADE_ROOT = Path(__file__).resolve().parents[1]
VENDOR_SCRIPTS = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts"
if str(VENDOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDOR_SCRIPTS))

from lgwf_env_init import existing_workflow  # noqa: E402


def read_json_object(path: Path, label: str = "json") -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_support() -> SimpleNamespace:
    return SimpleNamespace(
        workspace_layout=SimpleNamespace(
            lgwf_dir=lambda path: Path(path) / ".lgwf",
            processes_dir=lambda path: Path(path) / ".lgwf" / "processes",
        ),
        file_ops=SimpleNamespace(read_json_object=read_json_object),
        process_execution=SimpleNamespace(run_command=lambda command: SimpleNamespace(returncode=1, stdout="", stderr="")),
    )


def write_artifact_contract(work_dir: Path, outputs: list[str]) -> None:
    workflow_dir = work_dir / ".lgwf" / "workflow"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "workflow.json").write_text("{}", encoding="utf-8")
    (workflow_dir / "artifact_contracts.json").write_text(
        json.dumps({"run_managed_workspace_outputs": outputs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ExistingWorkflowRerunCleanupTests(unittest.TestCase):
    def test_rerun_existing_recreates_missing_work_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            args = SimpleNamespace(
                work_dir=str(work_dir),
                rerun_existing=True,
                continue_existing=False,
                resume_existing=False,
            )

            result = existing_workflow.handle_existing_workflow_data(args, io.StringIO(), io.StringIO(), make_support())

            self.assertIsNone(result)
            self.assertTrue(work_dir.is_dir())

    def test_rerun_existing_cleans_runtime_data_and_declared_outputs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            write_artifact_contract(work_dir, ["docs/steps", ".lgwf/custom_output.json"])
            (work_dir / ".lgwf" / "input_state.json").write_text("{}", encoding="utf-8")
            (work_dir / ".lgwf" / "context.json").write_text("{}", encoding="utf-8")
            (work_dir / ".lgwf" / "custom_output.json").write_text("{}", encoding="utf-8")
            (work_dir / ".lgwf" / "unmanaged_output.json").write_text("{}", encoding="utf-8")
            (work_dir / ".lgwf" / "runs" / "run-1").mkdir(parents=True)
            (work_dir / ".lgwf" / "runs" / "run-1" / "record.json").write_text("{}", encoding="utf-8")
            (work_dir / ".lgwf" / "codex").mkdir(parents=True)
            (work_dir / ".lgwf" / "codex" / "status.json").write_text("{}", encoding="utf-8")
            (work_dir / "docs" / "steps").mkdir(parents=True)
            (work_dir / "docs" / "steps" / "old-step.md").write_text("# old", encoding="utf-8")
            (work_dir / "docs" / "old-output.md").write_text("# old", encoding="utf-8")
            (work_dir / "scripts").mkdir()
            (work_dir / "scripts" / "foo.py").write_text("print('keep')\n", encoding="utf-8")
            (work_dir / "wf").mkdir()
            (work_dir / "wf" / "workflow.lgwf").write_text("workflow keep {}\n", encoding="utf-8")
            (work_dir / "README.md").write_text("# keep\n", encoding="utf-8")
            args = SimpleNamespace(
                work_dir=str(work_dir),
                rerun_existing=True,
                continue_existing=False,
                resume_existing=False,
            )

            result = existing_workflow.handle_existing_workflow_data(args, io.StringIO(), io.StringIO(), make_support())

            self.assertIsNone(result)
            self.assertTrue(work_dir.is_dir())
            self.assertFalse((work_dir / ".lgwf" / "runs").exists())
            self.assertFalse((work_dir / ".lgwf" / "codex").exists())
            self.assertFalse((work_dir / ".lgwf" / "workflow").exists())
            self.assertFalse((work_dir / ".lgwf" / "input_state.json").exists())
            self.assertFalse((work_dir / ".lgwf" / "context.json").exists())
            self.assertFalse((work_dir / ".lgwf" / "custom_output.json").exists())
            self.assertTrue((work_dir / ".lgwf" / "unmanaged_output.json").is_file())
            self.assertFalse((work_dir / "docs" / "steps").exists())
            self.assertTrue((work_dir / "docs" / "old-output.md").is_file())
            self.assertTrue((work_dir / "scripts" / "foo.py").is_file())
            self.assertTrue((work_dir / "wf" / "workflow.lgwf").is_file())
            self.assertTrue((work_dir / "README.md").is_file())

    def test_delete_existing_lgwf_data_keeps_undeclared_workspace_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            write_artifact_contract(work_dir, [])
            (work_dir / "docs" / "steps").mkdir(parents=True)
            (work_dir / "docs" / "steps" / "old-step.md").write_text("# old", encoding="utf-8")
            (work_dir / "input.json").write_text('{"repo_path":"."}', encoding="utf-8")

            existing_workflow.delete_existing_lgwf_data(work_dir, io.StringIO(), make_support())

            self.assertTrue(work_dir.is_dir())
            self.assertTrue((work_dir / "docs" / "steps" / "old-step.md").is_file())
            self.assertTrue((work_dir / "input.json").is_file())

    def test_delete_existing_lgwf_data_uses_current_workflow_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            workflow_dir = work_dir / ".lgwf" / "workflow"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "workflow.json").write_text("{}", encoding="utf-8")
            source_wf_dir = Path(tmp) / "source" / "wf"
            source_wf_dir.mkdir(parents=True)
            (source_wf_dir / "workflow.lgwf").write_text("workflow source {}\n", encoding="utf-8")
            (source_wf_dir / "artifact_contracts.json").write_text(
                json.dumps({"run_managed_workspace_outputs": ["docs/steps"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (work_dir / "docs" / "steps").mkdir(parents=True)
            (work_dir / "docs" / "steps" / "old-step.md").write_text("# old", encoding="utf-8")

            existing_workflow.delete_existing_lgwf_data(
                work_dir,
                io.StringIO(),
                make_support(),
                workflow_lgwf=str(source_wf_dir / "workflow.lgwf"),
            )

            self.assertFalse((work_dir / "docs" / "steps").exists())

    def test_delete_existing_lgwf_data_rejects_unsafe_managed_output_path(self) -> None:
        unsafe_values = ["../outside.txt", str(Path.cwd() / "outside.txt"), "C:outside.txt"]
        for unsafe_value in unsafe_values:
            with self.subTest(unsafe_value=unsafe_value):
                with tempfile.TemporaryDirectory() as tmp:
                    work_dir = Path(tmp) / "ws"
                    outside = Path(tmp) / "outside.txt"
                    outside.write_text("keep", encoding="utf-8")
                    write_artifact_contract(work_dir, [unsafe_value])
                    (work_dir / "README.md").write_text("# keep\n", encoding="utf-8")

                    with self.assertRaises(RuntimeError):
                        existing_workflow.delete_existing_lgwf_data(work_dir, io.StringIO(), make_support())

                    self.assertTrue(outside.is_file())
                    self.assertTrue((work_dir / "README.md").is_file())

    def test_delete_existing_lgwf_data_rejects_symlink_managed_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            target_dir = Path(tmp) / "target"
            target_dir.mkdir()
            write_artifact_contract(work_dir, ["linked"])
            try:
                os.symlink(target_dir, work_dir / "linked", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is not available: {exc}")

            with self.assertRaises(RuntimeError):
                existing_workflow.delete_existing_lgwf_data(work_dir, io.StringIO(), make_support())

            self.assertTrue((work_dir / "linked").is_symlink())
            self.assertTrue(target_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
