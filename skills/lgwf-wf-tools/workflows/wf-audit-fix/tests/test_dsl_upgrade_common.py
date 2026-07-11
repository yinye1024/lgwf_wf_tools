from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COMMON_PATH = PACKAGE_ROOT / "wf" / "shared" / "scripts" / "dsl_upgrade_common.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dsl_upgrade_common", COMMON_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class DslUpgradeCommonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_path_is_authorized_requires_target_inside_allowed_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "allowed"
            denied = root / "denied"
            allowed.mkdir()
            denied.mkdir()
            target = allowed / "workflow.lgwf"
            target.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")
            outside = denied / "workflow.lgwf"
            outside.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")

            self.assertTrue(self.module.path_is_authorized(target, [allowed]))
            self.assertFalse(self.module.path_is_authorized(outside, [allowed]))

    def test_build_audit_command_uses_bundled_lgwf_client(self) -> None:
        command = self.module.build_audit_command(Path("D:/demo/workflow.lgwf"))
        self.assertGreaterEqual(len(command), 4)
        self.assertEqual(command[-2], "audit")
        self.assertEqual(command[-1], "D:/demo/workflow.lgwf")
        self.assertTrue(command[1].replace("\\", "/").endswith("vendor/lgwf-client-assist/scripts/lgwf.py"))

    def test_diagnostic_identity_is_stable_for_same_finding(self) -> None:
        finding = {
            "code": "LGWF_EXAMPLE",
            "location": {"path": "wf/workflow.lgwf", "line": 12, "column": 4},
            "message": "示例问题",
        }
        identity = self.module.diagnostic_identity(finding)
        self.assertEqual(identity, self.module.diagnostic_identity(dict(finding)))
        self.assertIn("LGWF_EXAMPLE", identity)
        self.assertIn("wf/workflow.lgwf", identity)


if __name__ == "__main__":
    unittest.main()
