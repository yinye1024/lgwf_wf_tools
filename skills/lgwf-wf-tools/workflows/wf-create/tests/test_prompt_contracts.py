from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "wf"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class PromptContractTest(unittest.TestCase):
    def test_collect_raw_intent_drops_decision_routing(self) -> None:
        workflow = read("01_confirm_requirements/workflow.lgwf")
        self.assertNotIn("APPROVAL collect_raw_intent", workflow)
        self.assertIn("PY prepare_raw_intent_confirmation", workflow)
        self.assertIn("REVIEW confirm_raw_intent", workflow)
        self.assertIn("PY apply_confirmed_raw_intent", workflow)
        self.assertIn('PROMPT_REF "confirm_raw_intent.md"', workflow)
        self.assertIn('WRITE state.lgwf_wf_create.raw_intent_request', workflow)
        self.assertIn('PERSIST ".lgwf/raw_intent_approval.json"', workflow)
        raw_intent_block = re.search(r"REVIEW confirm_raw_intent.*?;", workflow, re.S)
        self.assertIsNotNone(raw_intent_block)
        self.assertNotIn("ROUTE_ON_DECISION", raw_intent_block.group(0))
        self.assertRegex(workflow, r"apply_confirmed_raw_intent\s+THEN\s+finish_raw_intent")
        self.assertIn("THEN finish_raw_intent", workflow)

    def test_finish_raw_intent_syncs_state_from_output_file(self) -> None:
        script = read("01_confirm_requirements/scripts/finish_raw_intent.py")
        self.assertIn('raw_intent_request.json', script)
        self.assertIn('"lgwf_wf_create.raw_intent_request"', script)

    def test_confirm_raw_intent_prompt_is_plain_output_prompt(self) -> None:
        prompt = read("01_confirm_requirements/confirm_raw_intent.md")
        self.assertIn("## Task", prompt)
        self.assertIn("## Output Format", prompt)
        self.assertIn("approve", prompt)
        self.assertIn("revise", prompt)
        self.assertNotIn("workflow control", prompt.lower())
        self.assertIn("approve` 不得携带空对象或完整业务 value", prompt)

    def test_structured_prompt_convert_context_is_supported_without_replacing_raw_intent(self) -> None:
        raw_prompt = read("01_confirm_requirements/confirm_raw_intent.md")
        raw_contract = read("01_confirm_requirements/resources/raw_intent_contract.md")
        requirements_prompt = read("01_confirm_requirements/agents/propose_requirements_react.md")
        business_prompt = read("02_confirm_business_flow/agents/propose_business_flow_react.md")

        for text in (raw_prompt, raw_contract, requirements_prompt, business_prompt):
            self.assertIn("source_business_contract", text)
            self.assertIn("conversion_mapping", text)
            self.assertIn("prompt_workflow_context", text)

        self.assertIn("raw_intent", raw_prompt)
        self.assertIn("兼容", raw_contract)
        self.assertIn("优先使用 `source_business_contract`", requirements_prompt)
        self.assertIn("优先使用 `conversion_mapping`", business_prompt)

    def test_creation_context_targets_are_available_to_three_design_stages(self) -> None:
        entry_contract = (ROOT.parent / "entry_contract.json").read_text(encoding="utf-8")
        raw_prompt = read("01_confirm_requirements/confirm_raw_intent.md")
        raw_contract = read("01_confirm_requirements/resources/raw_intent_contract.md")
        requirements_workflow = read("01_confirm_requirements/workflow.lgwf")
        business_workflow = read("02_confirm_business_flow/workflow.lgwf")
        step_workflow = read("03_confirm_step_designs/workflow.lgwf")
        requirements_prompt = read("01_confirm_requirements/agents/propose_requirements_react.md")
        business_prompt = read("02_confirm_business_flow/agents/propose_business_flow_react.md")
        step_prompt = read("03_confirm_step_designs/agents/design_steps_react.md")

        self.assertIn('"target_dir"', entry_contract)
        self.assertIn('"target_file"', entry_contract)
        self.assertIn('"target_dirs"', entry_contract)
        self.assertIn('"target_files"', entry_contract)
        self.assertIn("request.target_dir", raw_prompt)
        self.assertIn("request.target_file", raw_prompt)
        self.assertIn("creation_context_dirs", raw_contract)
        self.assertIn("creation_context_files", raw_contract)
        self.assertIn("creation_context_dirs", requirements_prompt)
        self.assertIn("creation_context_files", requirements_prompt)
        self.assertIn("creation_context_dirs", business_prompt)
        self.assertIn("creation_context_files", business_prompt)
        self.assertIn("creation_context_dirs", step_prompt)
        self.assertIn("creation_context_files", step_prompt)

        for workflow in (requirements_workflow, business_workflow, step_workflow):
            self.assertIn("TARGET_DIRS state.lgwf_wf_create.creation_context_dirs", workflow)
            self.assertIn("TARGET_FILES state.lgwf_wf_create.creation_context_files", workflow)

    def test_revision_prompts_are_revision_approval_prompts(self) -> None:
        for relative in (
            "01_confirm_requirements/revise_requirements.md",
            "02_confirm_business_flow/revise_business_flow.md",
            "03_confirm_step_designs/revise_step_designs.md",
        ):
            prompt = read(relative)
            self.assertIn("## Audit Scope", prompt)
            self.assertIn("## Audit Criteria", prompt)
            self.assertNotIn("修订落地 agent", prompt)
            self.assertNotIn("根据 revision feedback 调整", prompt)
            self.assertIn("approval decision record", prompt)

    def test_review_prompts_document_three_options_and_full_json_revise(self) -> None:
        for relative, context_key, review_node in (
            (
                "01_confirm_requirements/confirm_requirements.md",
                "requirements_confirmation_context.review_context_json",
                "confirm_requirements",
            ),
            (
                "02_confirm_business_flow/confirm_business_flow.md",
                "business_flow_confirmation_context.review_context_json",
                "confirm_business_flow",
            ),
            (
                "03_confirm_step_designs/confirm_step_designs.md",
                "step_design_confirmation_context.review_context_json",
                "confirm_step_designs",
            ),
        ):
            prompt = read(relative)
            self.assertIn("approve` / `revise` / `reject", prompt)
            self.assertIn(context_key, prompt)
            self.assertIn('"approval": "revise"', prompt)
            self.assertIn('"review_context_json"', prompt)
            self.assertIn("完整 JSON", prompt)
            self.assertIn(f"重新进入 `{review_node}` REVIEW 节点", prompt)

    def test_implementation_step_uses_deterministic_path_context(self) -> None:
        root_workflow = read("workflow.lgwf")
        workflow = read("03_confirm_step_designs/workflow.lgwf")
        implement_workflow = read("04_implement_steps_react/workflow.lgwf")
        observe_workflow = read("04_implement_steps_react/observe_audit.lgwf")
        spec = read("04_implement_steps_react/agents/spec.md")
        observe_prompt = read("04_implement_steps_react/agents/observe.md")
        self.assertIn("PY prepare_implementation_context", workflow)
        self.assertIn("apply_confirmed_step_designs THEN prepare_implementation_context", workflow)
        self.assertNotIn('READ workspace file ".lgwf/implementation_context.json";', workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_context.json";', workflow)
        self.assertIn('WORKFLOW "04_implement_steps_react/workflow.lgwf"', root_workflow)
        self.assertIn('SPEC "agents/spec.md"', implement_workflow)
        self.assertTrue((ROOT / "04_implement_steps_react/agents/spec.md").exists())
        self.assertFalse((ROOT / "03_confirm_step_designs/agents/implement_steps_react_spec.md").exists())
        self.assertIn('workspace file ".lgwf/implementation_context.json"', implement_workflow)
        self.assertIn('workspace file ".lgwf/implementation_observe.json"', implement_workflow)
        self.assertIn("target_package_abs", spec)
        self.assertIn("target_package_root` 是 `workspace_root` 相对路径", spec)
        self.assertIn("禁止从 `work_dir` 使用 `..`", spec)
        self.assertIn("OBSERVE WORKFLOW observe_audit", implement_workflow)
        self.assertIn("scripts/audit_created_package.py", observe_workflow)
        self.assertIn("CODEX observe_implementation", observe_workflow)
        self.assertNotIn("INSTRUCTION state.lgwf_wf_create.implementation_audit_result", observe_workflow)
        self.assertIn(".lgwf/implementation_audit_result.json", observe_workflow)
        self.assertIn(".lgwf/implementation_audit_result.json", observe_prompt)
        self.assertIn("脚本 audit", observe_prompt)

    def test_implementation_react_shared_rules_live_in_spec(self) -> None:
        spec = read("04_implement_steps_react/agents/spec.md")
        role_prompts = {
            "reason": read("04_implement_steps_react/agents/reason.md"),
            "act": read("04_implement_steps_react/agents/act.md"),
            "observe": read("04_implement_steps_react/agents/observe.md"),
        }

        self.assertIn("## ReAct 共同准则", spec)
        for required in (
            "`target_package_abs`",
            "`target_package_root` 是 `workspace_root` 相对路径",
            "禁止从 `work_dir` 使用 `..`",
            "`wf/docs/steps/`",
            "`implementation_result.generated_files`",
            "`workflow.lgwf` 只能生成在 `wf/workflow.lgwf` 或 `wf/<stage>/workflow.lgwf`",
            "不得生成 `wf/<stage>/<substage>/workflow.lgwf`",
            "裸 `INPUT state.*`",
            "不负责 `lgwf-wf-prompt-fix`",
        ):
            self.assertIn(required, spec)

        for name, prompt in role_prompts.items():
            self.assertIn("`agents/spec.md`", prompt, name)
            for duplicated_rule in (
                "`workflow.lgwf` 只能生成在",
                "不得生成 `wf/<stage>/<substage>/workflow.lgwf`",
                "根 `SKILL.md` 只允许",
                "裸 `INPUT state.*`",
                "不负责 `lgwf-wf-prompt-fix`",
            ):
                self.assertNotIn(duplicated_rule, prompt, name)

    def test_implementation_act_is_resumable_and_not_bound_to_default_timeout(self) -> None:
        workflow = read("04_implement_steps_react/workflow.lgwf")
        act_prompt = read("04_implement_steps_react/agents/act.md")
        reason_block = re.search(r"REASON CODEX.*?ACT CODEX", workflow, re.S)
        act_block = re.search(r"ACT CODEX.*?OBSERVE WORKFLOW", workflow, re.S)
        self.assertIsNotNone(reason_block)
        self.assertIsNotNone(act_block)
        self.assertRegex(reason_block.group(0), r"TIMEOUT\s+1200")
        self.assertRegex(act_block.group(0), r"TIMEOUT\s+3600")
        self.assertIn("已存在的目标 package", act_prompt)
        self.assertIn("续写草稿", act_prompt)
        self.assertIn("先补齐缺失的必需文件", act_prompt)

    def test_contract_enrichment_react_has_extended_codex_timeouts(self) -> None:
        workflow = read("05_enrich_contracts_react/workflow.lgwf")
        reason_block = re.search(r"REASON CODEX.*?ACT CODEX", workflow, re.S)
        act_block = re.search(r"ACT CODEX.*?OBSERVE WORKFLOW", workflow, re.S)
        self.assertIsNotNone(reason_block)
        self.assertIsNotNone(act_block)
        self.assertRegex(reason_block.group(0), r"TIMEOUT\s+1200")
        self.assertRegex(act_block.group(0), r"TIMEOUT\s+1800")


if __name__ == "__main__":
    unittest.main()
