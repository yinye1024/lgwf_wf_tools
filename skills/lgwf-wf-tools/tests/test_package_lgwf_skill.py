from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = FACADE_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import package_lgwf_skill  # noqa: E402


class PackageLgwfSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source-skill"
        self.runtime = self.root / "lgwf-client-assist"
        self.output_parent = self.root / "dist"
        self._create_source_skill()
        self._create_runtime()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create_source_skill(self) -> None:
        (self.source / "wf").mkdir(parents=True)
        (self.source / "ws" / ".lgwf").mkdir(parents=True)
        (self.source / ".local").mkdir()
        (self.source / "reports").mkdir()
        (self.source / "scripts").mkdir()
        (self.source / "SKILL.md").write_text("---\nname: source-skill\n---\n", encoding="utf-8")
        (self.source / "AGENTS.md").write_text("# 源 skill 指引\n", encoding="utf-8")
        (self.source / "README.md").write_text("# source-skill\n", encoding="utf-8")
        (self.source / "wf" / "workflow.lgwf").write_text("workflow test {}\n", encoding="utf-8")
        (self.source / "scripts" / "tool.py").write_text("print('ok')\n", encoding="utf-8")
        (self.source / "ws" / ".lgwf" / "state.json").write_text("{}", encoding="utf-8")
        (self.source / ".local" / "draft.json").write_text("{}", encoding="utf-8")
        (self.source / "reports" / "old.md").write_text("old", encoding="utf-8")

    def _create_runtime(self) -> None:
        (self.runtime / "scripts").mkdir(parents=True)
        (self.runtime / "references").mkdir()
        (self.runtime / "__pycache__").mkdir()
        (self.runtime / "scripts" / "lgwf.py").write_text("print('lgwf')\n", encoding="utf-8")
        (self.runtime / "AGENTS.md").write_text("# runtime\n", encoding="utf-8")
        (self.runtime / "__pycache__" / "x.pyc").write_bytes(b"x")

    def test_packages_skill_with_bundled_runtime_and_local_runner(self) -> None:
        result = package_lgwf_skill.package_skill(
            source_skill=self.source,
            output_parent=self.output_parent,
            runtime_source=self.runtime,
        )

        packaged = (self.output_parent / "source-skill").resolve()
        self.assertEqual(result.output_skill, packaged)
        self.assertTrue((packaged / "SKILL.md").is_file())
        self.assertTrue((packaged / "wf" / "workflow.lgwf").is_file())
        self.assertTrue((packaged / "scripts" / "tool.py").is_file())
        self.assertTrue((packaged / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py").is_file())
        self.assertTrue((packaged / "scripts" / "run_local_lgwf_workflow.py").is_file())
        self.assertFalse((packaged / "ws").exists())
        self.assertFalse((packaged / ".local").exists())
        self.assertFalse((packaged / "reports").exists())
        self.assertFalse((packaged / "vendor" / "lgwf-client-assist" / "__pycache__").exists())

        manifest = json.loads((packaged / "PACKAGING_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["packager"], "lgwf-wf-tools/skill-packaging")
        self.assertEqual(manifest["source_skill_name"], "source-skill")
        self.assertEqual(manifest["runtime_relative_path"], "vendor/lgwf-client-assist")
        self.assertIn("ws", manifest["excluded_names"])

    def test_refuses_to_overwrite_existing_output_without_force(self) -> None:
        target = self.output_parent / "source-skill"
        target.mkdir(parents=True)

        with self.assertRaisesRegex(FileExistsError, "already exists"):
            package_lgwf_skill.package_skill(
                source_skill=self.source,
                output_parent=self.output_parent,
                runtime_source=self.runtime,
            )

    def test_requires_workflow_lgwf(self) -> None:
        (self.source / "wf" / "workflow.lgwf").unlink()

        with self.assertRaisesRegex(FileNotFoundError, "wf/workflow.lgwf"):
            package_lgwf_skill.package_skill(
                source_skill=self.source,
                output_parent=self.output_parent,
                runtime_source=self.runtime,
            )

    def test_default_runtime_source_uses_facade_vendor(self) -> None:
        expected = FACADE_ROOT / "vendor" / "lgwf-client-assist"

        self.assertEqual(package_lgwf_skill._default_runtime_source(), expected)


if __name__ == "__main__":
    unittest.main()
