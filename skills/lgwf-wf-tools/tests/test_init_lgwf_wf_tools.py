from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
