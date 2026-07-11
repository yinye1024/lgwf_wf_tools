from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = FACADE_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import package_lgwf_wf_tools_zip  # noqa: E402


class PackageLgwfWfToolsZipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "lgwf-wf-tools"
        self.output = self.root / "dist" / "lgwf-wf-tools.zip"
        self._create_source_tree()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create_source_tree(self) -> None:
        (self.source / "scripts").mkdir(parents=True)
        (self.source / "docs").mkdir()
        (self.source / ".local" / "runs").mkdir(parents=True)
        (self.source / "workflows" / "demo" / "ws" / ".lgwf").mkdir(parents=True)
        (self.source / "scripts" / "__pycache__").mkdir(parents=True)
        (self.source / "assets").mkdir()
        (self.source / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        (self.source / "AGENTS.md").write_text("# 指引\n", encoding="utf-8")
        (self.source / "README.md").write_text("# 说明\n", encoding="utf-8")
        (self.source / "registry.json").write_text('{"workflows": []}\n', encoding="utf-8")
        (self.source / "scripts" / "tool.py").write_text("print('ok')\n", encoding="utf-8")
        (self.source / "docs" / "使用说明.md").write_text("中文内容\n", encoding="utf-8")
        (self.source / ".local" / "runs" / "large.json").write_text("x" * 1024, encoding="utf-8")
        (self.source / "workflows" / "demo" / "workflow.lgwf").write_text("workflow demo {}\n", encoding="utf-8")
        (self.source / "workflows" / "demo" / "ws" / ".lgwf" / "state.json").write_text(
            "{}\n",
            encoding="utf-8",
        )
        (self.source / "scripts" / "__pycache__" / "tool.pyc").write_bytes(b"cache")
        (self.source / "assets" / "keep.txt").write_text("keep\n", encoding="utf-8")

    def test_creates_zip_with_facade_root_and_excludes_local_state(self) -> None:
        result = package_lgwf_wf_tools_zip.package_facade_zip(
            source_root=self.source,
            output_zip=self.output,
        )

        self.assertEqual(result.output_zip, self.output.resolve())
        self.assertGreaterEqual(result.included_file_count, 5)
        self.assertIn(".local", result.excluded_names)
        self.assertTrue(self.output.is_file())

        with zipfile.ZipFile(self.output) as archive:
            names = set(archive.namelist())

        self.assertIn("lgwf-wf-tools/SKILL.md", names)
        self.assertIn("lgwf-wf-tools/AGENTS.md", names)
        self.assertIn("lgwf-wf-tools/README.md", names)
        self.assertIn("lgwf-wf-tools/scripts/tool.py", names)
        self.assertIn("lgwf-wf-tools/docs/使用说明.md", names)
        self.assertIn("lgwf-wf-tools/assets/keep.txt", names)
        self.assertIn("lgwf-wf-tools/workflows/demo/workflow.lgwf", names)
        self.assertFalse(any("/.local/" in name or name.startswith("lgwf-wf-tools/.local/") for name in names))
        self.assertFalse(any("/.lgwf/" in name or name.startswith("lgwf-wf-tools/.lgwf/") for name in names))
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith(".pyc") for name in names))

    def test_overwrites_existing_zip_by_default(self) -> None:
        self.output.parent.mkdir(parents=True)
        self.output.write_bytes(b"existing")

        package_lgwf_wf_tools_zip.package_facade_zip(
            source_root=self.source,
            output_zip=self.output,
        )

        with zipfile.ZipFile(self.output) as archive:
            self.assertIn("lgwf-wf-tools/SKILL.md", archive.namelist())

    def test_can_refuse_to_overwrite_existing_zip(self) -> None:
        self.output.parent.mkdir(parents=True)
        self.output.write_bytes(b"existing")

        with self.assertRaisesRegex(FileExistsError, "already exists"):
            package_lgwf_wf_tools_zip.package_facade_zip(
                source_root=self.source,
                output_zip=self.output,
                force=False,
            )

    def test_default_output_zip_uses_output_directory(self) -> None:
        self.assertEqual(
            package_lgwf_wf_tools_zip.default_output_zip(),
            FACADE_ROOT / "output" / "lgwf-wf-tools.zip",
        )


if __name__ == "__main__":
    unittest.main()
