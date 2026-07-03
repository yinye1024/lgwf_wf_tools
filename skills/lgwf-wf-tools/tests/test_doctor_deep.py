from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = FACADE_ROOT / "scripts" / "doctor_lgwf_wf_tools.py"


def load_doctor_module():
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    spec = importlib.util.spec_from_file_location("doctor_lgwf_wf_tools", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DoctorDeepTest(unittest.TestCase):
    def test_deep_doctor_passes(self) -> None:
        module = load_doctor_module()
        result = module.run_doctor(deep=True)
        failed = [item["label"] for item in result["checks"] if not item.get("passed")]
        failed.extend(item["label"] for item in result.get("deep_checks", []) if not item.get("passed"))
        self.assertEqual([], failed)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
