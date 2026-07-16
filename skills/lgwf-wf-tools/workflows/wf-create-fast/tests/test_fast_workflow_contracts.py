from __future__ import annotations

import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class FastWorkflowContractTests(unittest.TestCase):
    def test_package_structure_exists(self) -> None:
        required_paths = [
            "entry_contract.json",
            "wf/workflow.lgwf",
            "wf/03_materialize_scaffold/workflow.lgwf",
            "wf/04_main_agent_handoff/workflow.lgwf",
        ]
        for relative in required_paths:
            with self.subTest(relative=relative):
                self.assertTrue((PACKAGE_ROOT / relative).is_file())

    def test_removed_standard_back_half(self) -> None:
        removed_dirs = [
            "self-improve",
            "wf/03_confirm_step_designs",
            "wf/04_implement_steps_react",
            "wf/06_summarize_create_result",
            "wf/07_post_fix_handoff",
            ".local",
            "ws/.lgwf",
            "ws/reports",
        ]
        for relative in removed_dirs:
            with self.subTest(relative=relative):
                self.assertFalse((PACKAGE_ROOT / relative).exists())

    def test_root_flow_sequence_and_forbidden_refs(self) -> None:
        text = (PACKAGE_ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("WORKFLOW lgwf_wf_create_fast;", text)
        self.assertIn('WORKFLOW "03_materialize_scaffold/workflow.lgwf"', text)
        self.assertIn('WORKFLOW "04_main_agent_handoff/workflow.lgwf"', text)
        self.assertIn(
            "FLOW define_requirements\n"
            "  THEN design_structure\n"
            "  THEN materialize_scaffold\n"
            "  THEN main_agent_handoff;",
            text,
        )
        forbidden = [
            "03_confirm_step_designs",
            "04_implement_steps_react",
            "step_designs.json",
            "post_fix_handoff",
        ]
        for needle in forbidden:
            with self.subTest(needle=needle):
                self.assertNotIn(needle, text)

if __name__ == "__main__":
    unittest.main()
