from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PACKAGE_ROOT / "wf" / "03_materialize_scaffold" / "scripts" / "materialize_scaffold.py"


def load_materialize_module():
    spec = importlib.util.spec_from_file_location("wf_create_fast_materialize_scaffold", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MaterializeScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_materialize_module()

    def make_work_dir(self, root: Path) -> Path:
        (root / ".git").mkdir()
        work_dir = root / "skills" / "lgwf-wf-tools" / "workflows" / "wf-create-fast" / "ws"
        (work_dir / ".lgwf").mkdir(parents=True)
        (work_dir / ".lgwf" / "create_requirements.json").write_text(
            json.dumps(
                {
                    "confirmed": {
                        "workflow_name": "demo-workflow",
                        "target_package_root": "skills/demo-workflow",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (work_dir / ".lgwf" / "business_flow.json").write_text(
            json.dumps(
                {
                    "confirmed": {
                        "workflow_name": "demo-workflow",
                        "target_package_root": "skills/demo-workflow",
                        "stages": [
                            {"stage_id": "prepare"},
                            {"stage_id": "execute"},
                        ],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return work_dir

    def write_scaffold_plan(self, work_dir: Path, *, target_package_root: str = "skills/demo-workflow") -> None:
        plan = {
            "workflow_name": "demo-workflow",
            "target_package_root": target_package_root,
            "package_profile": "internal_workflow_package",
            "stage_manifest": [
                {"stage_id": "prepare", "stage_dir": "01_prepare"},
                {"stage_id": "execute", "stage_dir": "02_execute"},
            ],
            "create_dirs": [
                "scripts",
                "tests",
                "ws",
                "wf",
                "wf/shared/scripts",
                "wf/01_prepare/scripts",
                "wf/02_execute/scripts",
            ],
            "create_files": [
                "AGENTS.md",
                "README.md",
                "entry_contract.json",
                "wf/workflow.lgwf",
                "wf/artifact_contracts.json",
                "wf/01_prepare/workflow.lgwf",
                "wf/01_prepare/artifact_contracts.json",
                "wf/01_prepare/scripts/run.py",
                "wf/02_execute/workflow.lgwf",
                "wf/02_execute/artifact_contracts.json",
                "wf/02_execute/scripts/run.py",
                "tests/test_workflow_structure.py",
                "tests/README.md",
            ],
        }
        (work_dir / ".lgwf" / "scaffold_package_result.json").write_text(
            json.dumps({"scaffold_plan": plan}, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_materializes_minimal_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            work_dir = self.make_work_dir(workspace_root)
            self.write_scaffold_plan(work_dir)

            result = self.module.materialize_scaffold(work_dir)

            target = workspace_root / "skills" / "demo-workflow"
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["target_package_root"], "skills/demo-workflow")
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "wf" / "workflow.lgwf").is_file())
            self.assertTrue((target / "wf" / "01_prepare" / "scripts" / "run.py").is_file())
            self.assertFalse((target / ".lgwf").exists())
            workflow_text = (target / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
            self.assertIn('WORKFLOW "01_prepare/workflow.lgwf"', workflow_text)
            self.assertIn('WORKFLOW "02_execute/workflow.lgwf"', workflow_text)
            written = json.loads((work_dir / ".lgwf" / "materialize_scaffold_result.json").read_text(encoding="utf-8"))
            self.assertTrue(written["handoff_ready"])

    def test_rejects_unsafe_target_package_root(self) -> None:
        bad_roots = [
            "D:/bad-workflow",
            "/bad-workflow",
            "../bad-workflow",
            "https://example.com/workflow",
            "skills/.lgwf/bad-workflow",
        ]
        for bad_root in bad_roots:
            with self.subTest(bad_root=bad_root), tempfile.TemporaryDirectory() as tmp:
                work_dir = self.make_work_dir(Path(tmp))
                self.write_scaffold_plan(work_dir, target_package_root=bad_root)
                with self.assertRaises(ValueError):
                    self.module.materialize_scaffold(work_dir)

    def test_skips_non_empty_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            work_dir = self.make_work_dir(workspace_root)
            self.write_scaffold_plan(work_dir)
            readme = workspace_root / "skills" / "demo-workflow" / "README.md"
            readme.parent.mkdir(parents=True)
            readme.write_text("keep me\n", encoding="utf-8")

            result = self.module.materialize_scaffold(work_dir)

            self.assertEqual(result["status"], "partial_existing_files")
            self.assertIn("README.md", result["skipped_existing_files"])
            self.assertEqual(readme.read_text(encoding="utf-8"), "keep me\n")


if __name__ == "__main__":
    unittest.main()
