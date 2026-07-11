from __future__ import annotations

import sys
import unittest
from pathlib import Path


SKELETON_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = SKELETON_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import list_workflows  # noqa: E402
import validate_registry  # noqa: E402


class RegistryTemplateTests(unittest.TestCase):
    def test_registry_validation_passes(self) -> None:
        result = validate_registry.run_validation()
        failed = [check for check in result["checks"] if not check.get("passed")]
        self.assertEqual(failed, [])
        self.assertTrue(result["passed"])

    def test_list_workflows_reports_examples(self) -> None:
        result = list_workflows.list_workflows()
        workflows = {item["id"]: item for item in result["workflows"]}
        self.assertEqual(set(workflows), {"example-workflow", "example-tool-workflow"})
        self.assertEqual(workflows["example-workflow"]["input_mode"], "input_json_required")
        self.assertEqual(workflows["example-tool-workflow"]["input_mode"], "tool_args")


if __name__ == "__main__":
    unittest.main()
