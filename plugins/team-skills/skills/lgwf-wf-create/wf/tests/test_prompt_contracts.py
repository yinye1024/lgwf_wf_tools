from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class PromptContractTest(unittest.TestCase):
    def test_collect_raw_intent_drops_decision_routing(self) -> None:
        workflow = read("02_confirm_requirements/00_collect_raw_intent/workflow.lgwf")
        self.assertIn("APPROVAL confirm_raw_intent", workflow)
        self.assertIn('PROMPT_REF "confirm_raw_intent.md"', workflow)
        self.assertIn('WRITE state.lgwf_wf_create.raw_intent_request', workflow)
        self.assertIn('PERSIST ".lgwf/raw_intent_request.json"', workflow)
        self.assertNotIn("ROUTE_ON_DECISION", workflow)
        self.assertIn("confirm_raw_intent THEN finish_raw_intent", workflow)

    def test_finish_raw_intent_syncs_state_from_output_file(self) -> None:
        script = read("02_confirm_requirements/00_collect_raw_intent/scripts/finish_raw_intent.py")
        self.assertIn('raw_intent_request.json', script)
        self.assertIn('"lgwf_wf_create.raw_intent_request"', script)

    def test_confirm_raw_intent_prompt_is_plain_output_prompt(self) -> None:
        prompt = read("02_confirm_requirements/00_collect_raw_intent/confirm_raw_intent.md")
        self.assertIn("## Success Criteria", prompt)
        self.assertIn("## Output Format", prompt)
        self.assertNotIn("decision", prompt.lower())
        self.assertNotIn("workflow control", prompt.lower())
        self.assertIn("只写入 `.lgwf/raw_intent_request.json`", prompt)

    def test_revision_prompts_are_revision_approval_prompts(self) -> None:
        for relative in (
            "02_confirm_requirements/revise_requirements.md",
            "04_confirm_business_flow/revise_business_flow.md",
            "07_confirm_step_designs/revise_step_designs.md",
        ):
            prompt = read(relative)
            self.assertIn("## Audit Scope", prompt)
            self.assertIn("## Audit Criteria", prompt)
            self.assertNotIn("修订落地 agent", prompt)
            self.assertNotIn("根据 revision feedback 调整", prompt)
            self.assertIn("approval decision record", prompt)


if __name__ == "__main__":
    unittest.main()
