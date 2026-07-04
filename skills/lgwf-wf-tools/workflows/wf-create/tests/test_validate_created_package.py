from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PACKAGE_ROOT / "wf" / "scripts" / "validate_created_package.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_created_package", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class ValidateCreatedPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def make_work_dir(self, root: Path, stages: list[str]) -> Path:
        work_dir = root / "workflows" / "wf-create" / "ws"
        lgwf_dir = work_dir / ".lgwf"
        target_root = root / "skills" / "demo-workflow"
        (target_root / "wf").mkdir(parents=True)
        (target_root / "wf" / "workflow.lgwf").write_text("WORKFLOW demo;\nENTRY done;\n", encoding="utf-8")
        write_json(
            lgwf_dir / "implementation_context.json",
            {
                "workspace_root": str(root),
                "target_package_root": "skills/demo-workflow",
                "target_package_abs": str(target_root),
            },
        )
        write_json(
            lgwf_dir / "implementation_result.json",
            {"target_package_root": "skills/demo-workflow", "status": "implemented"},
        )
        write_json(
            lgwf_dir / "step_designs.json",
            {
                "confirmed": {
                    "target_package_root": "skills/demo-workflow",
                    "source_business_flow_stages": [{"stage_id": stage} for stage in stages],
                }
            },
        )
        return work_dir

    def add_stage(self, target_root: Path, stage: str) -> None:
        stage_root = target_root / "wf" / stage
        for rel in ("agents", "scripts", "resources"):
            (stage_root / rel).mkdir(parents=True, exist_ok=True)
        (stage_root / "workflow.lgwf").write_text("WORKFLOW stage;\nENTRY done;\n", encoding="utf-8")

    def test_validate_created_package_accepts_confirmed_stage_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare", "finish"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "prepare")
            self.add_stage(target_root, "finish")
            self.module.run_authoring_audit = lambda workflow_lgwf, workspace_root: {
                "ok": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }

            result = self.module.validate_created_package(work_dir)

            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["stage_ids"], ["prepare", "finish"])
            self.assertTrue((work_dir / ".lgwf" / "created_package_validation.json").exists())

    def test_validate_created_package_rejects_missing_confirmed_stage_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            for rel in ("agents", "scripts", "resources"):
                (target_root / "wf" / "prepare" / rel).mkdir(parents=True, exist_ok=True)
            self.module.run_authoring_audit = lambda workflow_lgwf, workspace_root: {
                "ok": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }

            with self.assertRaises(RuntimeError) as raised:
                self.module.validate_created_package(work_dir)

            self.assertIn("stage prepare workflow.lgwf", str(raised.exception))

    def test_validate_created_package_rejects_missing_stage_private_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            stage_root = root / "skills" / "demo-workflow" / "wf" / "prepare"
            stage_root.mkdir(parents=True)
            (stage_root / "workflow.lgwf").write_text("WORKFLOW stage;\nENTRY done;\n", encoding="utf-8")
            self.module.run_authoring_audit = lambda workflow_lgwf, workspace_root: {
                "ok": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
            }

            with self.assertRaises(RuntimeError) as raised:
                self.module.validate_created_package(work_dir)

            self.assertIn("stage prepare agents/", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
