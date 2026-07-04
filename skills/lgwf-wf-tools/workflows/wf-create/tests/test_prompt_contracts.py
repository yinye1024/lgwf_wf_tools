from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "wf"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class PromptContractTest(unittest.TestCase):
    def test_collect_raw_intent_drops_decision_routing(self) -> None:
        workflow = read("02_confirm_requirements/workflow.lgwf")
        self.assertIn("APPROVAL collect_raw_intent", workflow)
        self.assertIn('PROMPT_REF "confirm_raw_intent.md"', workflow)
        self.assertIn('WRITE state.lgwf_wf_create.raw_intent_request', workflow)
        self.assertIn('PERSIST ".lgwf/raw_intent_request.json"', workflow)
        raw_intent_block = re.search(r"APPROVAL collect_raw_intent.*?;", workflow, re.S)
        self.assertIsNotNone(raw_intent_block)
        self.assertNotIn("ROUTE_ON_DECISION", raw_intent_block.group(0))
        self.assertIn("collect_raw_intent THEN finish_raw_intent", workflow)
        self.assertIn("THEN finish_raw_intent", workflow)

    def test_finish_raw_intent_syncs_state_from_output_file(self) -> None:
        script = read("02_confirm_requirements/scripts/finish_raw_intent.py")
        self.assertIn('raw_intent_request.json', script)
        self.assertIn('"lgwf_wf_create.raw_intent_request"', script)

    def test_confirm_raw_intent_prompt_is_plain_output_prompt(self) -> None:
        prompt = read("02_confirm_requirements/confirm_raw_intent.md")
        self.assertIn("## Success Criteria", prompt)
        self.assertIn("## Output Format", prompt)
        self.assertNotIn("decision", prompt.lower())
        self.assertNotIn("workflow control", prompt.lower())
        self.assertIn("只写入 `.lgwf/raw_intent_request.json`", prompt)

    def test_structured_prompt_convert_context_is_supported_without_replacing_raw_intent(self) -> None:
        raw_prompt = read("02_confirm_requirements/confirm_raw_intent.md")
        raw_contract = read("02_confirm_requirements/resources/raw_intent_contract.md")
        requirements_prompt = read("02_confirm_requirements/agents/propose_requirements_react.md")
        business_prompt = read("04_confirm_business_flow/agents/propose_business_flow_react.md")

        for text in (raw_prompt, raw_contract, requirements_prompt, business_prompt):
            self.assertIn("source_business_contract", text)
            self.assertIn("conversion_mapping", text)
            self.assertIn("prompt_workflow_context", text)

        self.assertIn("raw_intent", raw_prompt)
        self.assertIn("兼容", raw_contract)
        self.assertIn("优先使用 `source_business_contract`", requirements_prompt)
        self.assertIn("优先使用 `conversion_mapping`", business_prompt)

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

    def test_implementation_step_uses_deterministic_path_context(self) -> None:
        workflow = read("07_confirm_step_designs/workflow.lgwf")
        prompt = read("07_confirm_step_designs/agents/implement_steps_react.md")
        self.assertIn("PY prepare_implementation_context", workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/implementation_context.json"', workflow)
        self.assertIn("apply_confirmed_step_designs THEN prepare_implementation_context THEN implement_steps_react", workflow)
        self.assertIn("target_package_abs", prompt)
        self.assertIn("target_package_root` 是 `workspace_root` 相对路径", prompt)
        self.assertIn("禁止从 `work_dir` 使用 `..`", prompt)


if __name__ == "__main__":
    unittest.main()
