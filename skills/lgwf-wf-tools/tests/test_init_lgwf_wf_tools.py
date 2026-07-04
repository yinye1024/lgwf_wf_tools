from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import init_lgwf_wf_tools


class InitLgwfWfToolsTest(unittest.TestCase):
    def test_install_bundled_lgwf_uses_current_vendor_install_api(self) -> None:
        result = init_lgwf_wf_tools.install_bundled_lgwf()

        self.assertTrue(result["passed"], result)
        self.assertFalse(result["skipped"], result)
        self.assertTrue(result["wheel"], result)
        self.assertTrue(result["wheel_sha256"], result)
        self.assertEqual("0.1.1", result["bundled_version"])
        self.assertEqual("0.1.1", result["installed_version"])

    def test_ensure_codex_skill_installation_creates_missing_link_to_self(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            facade_root = temp / "repo" / "skills" / "lgwf-wf-tools"
            facade_root.mkdir(parents=True)
            (facade_root / "SKILL.md").write_text("---\nname: lgwf-wf-tools\n---\n", encoding="utf-8")
            codex_home = temp / ".codex"

            result = init_lgwf_wf_tools.ensure_codex_skill_installation(facade_root=facade_root, codex_home=codex_home)

            self.assertTrue(result["passed"], result)
            self.assertEqual(str(facade_root.resolve()), result["expected_target"])
            self.assertEqual(str(codex_home / "skills" / "lgwf-wf-tools"), result["install_path"])
            self.assertIn("created_skill_link", result["actions"])
            self.assertEqual(facade_root.resolve(), (codex_home / "skills" / "lgwf-wf-tools").resolve())

    def test_ensure_codex_skill_installation_replaces_plain_directory_with_link(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            facade_root = temp / "repo" / "skills" / "lgwf-wf-tools"
            facade_root.mkdir(parents=True)
            (facade_root / "SKILL.md").write_text("---\nname: lgwf-wf-tools\n---\n", encoding="utf-8")
            install_path = temp / ".codex" / "skills" / "lgwf-wf-tools"
            install_path.mkdir(parents=True)
            (install_path / "SKILL.md").write_text("old copy\n", encoding="utf-8")

            result = init_lgwf_wf_tools.ensure_codex_skill_installation(facade_root=facade_root, codex_home=temp / ".codex")

            self.assertTrue(result["passed"], result)
            self.assertIn("backed_up_existing_skill_directory", result["actions"])
            self.assertIn("created_skill_link", result["actions"])
            self.assertEqual(facade_root.resolve(), install_path.resolve())
            backup_path = Path(result["backup_path"])
            self.assertTrue((backup_path / "SKILL.md").is_file(), result)

    def test_ensure_codex_skill_installation_repoints_wrong_link_to_self(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            temp = Path(raw_temp)
            facade_root = temp / "repo" / "skills" / "lgwf-wf-tools"
            old_target = temp / "old" / "skills" / "lgwf-wf-tools"
            facade_root.mkdir(parents=True)
            old_target.mkdir(parents=True)
            (facade_root / "SKILL.md").write_text("---\nname: lgwf-wf-tools\n---\n", encoding="utf-8")
            codex_home = temp / ".codex"
            install_path = codex_home / "skills" / "lgwf-wf-tools"
            install_path.parent.mkdir(parents=True)
            init_lgwf_wf_tools.create_directory_link(install_path, old_target)

            result = init_lgwf_wf_tools.ensure_codex_skill_installation(facade_root=facade_root, codex_home=codex_home)

            self.assertTrue(result["passed"], result)
            self.assertIn("removed_wrong_skill_link", result["actions"])
            self.assertIn("created_skill_link", result["actions"])
            self.assertEqual(facade_root.resolve(), install_path.resolve())


if __name__ == "__main__":
    unittest.main()
