from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LgwfPackagingDocsTest(unittest.TestCase):
    def test_bundled_client_copy_path_matches_skills_layout(self) -> None:
        maintenance = ROOT / "skills" / "lgwf-wf-tools" / "docs" / "maintenance.md"
        text = maintenance.read_text(encoding="utf-8")

        self.assertIn(
            r"skills\lgwf-wf-tools\assets\lgwf-client-assist.zip",
            text,
        )
        self.assertNotIn("plugins/team-skills", text)
        self.assertNotIn(r"plugins\team-skills", text)


if __name__ == "__main__":
    unittest.main()
