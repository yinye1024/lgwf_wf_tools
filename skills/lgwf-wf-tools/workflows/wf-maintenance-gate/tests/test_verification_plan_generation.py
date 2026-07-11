from __future__ import annotations

import sys
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SHARED = PACKAGE_ROOT / "wf" / "shared" / "scripts"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from maintenance_gate_common import build_verification_plan


class VerificationPlanGenerationTests(unittest.TestCase):
    def test_deep_doctor_stays_skipped_when_flag_is_false(self) -> None:
        impact = {
            "categories": ["shared_contract"],
            "impacted_workflows": [],
            "risk": "high",
        }
        request = {"allow_deep_doctor": False, "verification_level": "standard"}
        plan = build_verification_plan(impact, request)
        self.assertTrue(any(item["check_id"] == "deep_doctor" for item in plan["skipped_or_suggested_checks"]))

    def test_workflow_tests_created_for_impacted_workflows(self) -> None:
        impact = {
            "categories": ["workflow_source"],
            "impacted_workflows": ["wf-create"],
            "risk": "high",
        }
        request = {"allow_workflow_tests": True}
        plan = build_verification_plan(impact, request)
        self.assertTrue(any(item["check_id"] == "workflow_tests:wf-create" for item in plan["commands"]))

    def test_package_smoke_blocked_without_output_zip(self) -> None:
        impact = {
            "categories": ["packaging"],
            "impacted_workflows": [],
            "risk": "high",
        }
        request = {"intent": "package_ready", "allow_package_smoke": True, "output_zip": None}
        plan = build_verification_plan(impact, request)
        self.assertEqual(plan["zip_conflict"]["status"], "needs_review")
        self.assertTrue(any(item["check_id"] == "package_smoke" for item in plan["blocked_commands"]))


if __name__ == "__main__":
    unittest.main()
