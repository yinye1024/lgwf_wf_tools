from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "wf"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class PromptContractTest(unittest.TestCase):
    def test_collect_raw_intent_drops_decision_routing(self) -> None:
        workflow = read("01_confirm_requirements/01_raw_intent/workflow.lgwf")
        self.assertNotIn("APPROVAL collect_raw_intent", workflow)
        self.assertIn("PY prepare_raw_intent_confirmation", workflow)
        self.assertIn("REVIEW confirm_raw_intent", workflow)
        self.assertIn("PY apply_confirmed_raw_intent", workflow)
        self.assertIn('PROMPT_REF "agents/confirm_raw_intent.md"', workflow)
        self.assertIn('WRITE state.lgwf_wf_create.raw_intent_request', workflow)
        self.assertIn('PERSIST ".lgwf/raw_intent_approval.json"', workflow)
        raw_intent_block = re.search(r"REVIEW confirm_raw_intent.*?;", workflow, re.S)
        self.assertIsNotNone(raw_intent_block)
        self.assertNotIn("ROUTE_ON_DECISION", raw_intent_block.group(0))
        self.assertRegex(workflow, r"apply_confirmed_raw_intent\s+THEN\s+finish_raw_intent")
        self.assertIn("THEN finish_raw_intent", workflow)

    def test_finish_raw_intent_syncs_state_from_output_file(self) -> None:
        script = read("01_confirm_requirements/01_raw_intent/scripts/finish_raw_intent.py")
        self.assertIn('raw_intent_request.json', script)
        self.assertIn('"lgwf_wf_create.raw_intent_request"', script)

    def test_confirm_raw_intent_prompt_is_plain_output_prompt(self) -> None:
        prompt = read("01_confirm_requirements/01_raw_intent/agents/confirm_raw_intent.md")
        self.assertIn("## Task", prompt)
        self.assertIn("## Output Format", prompt)
        self.assertIn("主 agent", prompt)
        self.assertIn("人工确认展示模板", prompt)
        self.assertIn("确认原因", prompt)
        self.assertIn("提交值", prompt)
        self.assertIn("approve", prompt)
        self.assertIn("revise", prompt)
        self.assertNotIn("workflow control", prompt.lower())
        self.assertIn("approve` 不得携带空对象或完整业务 value", prompt)
        self.assertIn("revise` 提交完整更新后的 `review_context_json`", prompt)
        self.assertIn("不得读取、摘要或执行这些路径里的内容", prompt)
        self.assertIn("后续需求 proposal 节点", prompt)
        self.assertNotIn("是否已经吸收参考资料", prompt)

    def test_structured_prompt_convert_context_is_supported_without_replacing_raw_intent(self) -> None:
        raw_prompt = read("01_confirm_requirements/01_raw_intent/agents/confirm_raw_intent.md")
        requirements_prompt = read("01_confirm_requirements/02_requirements_proposal/agents/propose_requirements.md")
        business_prompt = read("02_confirm_business_flow/01_business_flow_proposal/agents/propose_business_flow.md")

        for text in (raw_prompt, requirements_prompt, business_prompt):
            self.assertIn("source_business_contract", text)
            self.assertIn("conversion_mapping", text)
            self.assertIn("prompt_workflow_context", text)

        self.assertIn("raw_intent", raw_prompt)
        self.assertIn("优先使用 `source_business_contract`", requirements_prompt)
        self.assertIn("优先使用 `conversion_mapping`", business_prompt)

    def test_creation_context_targets_are_available_only_until_confirmed_business_flow(self) -> None:
        entry_contract = (ROOT.parent / "entry_contract.json").read_text(encoding="utf-8")
        agents_md = (ROOT.parent / "AGENTS.md").read_text(encoding="utf-8")
        readme = (ROOT.parent / "README.md").read_text(encoding="utf-8")
        raw_prompt = read("01_confirm_requirements/01_raw_intent/agents/confirm_raw_intent.md")
        requirements_workflow = read("01_confirm_requirements/02_requirements_proposal/workflow.lgwf")
        business_workflow = read("02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf")
        requirements_prompt = read("01_confirm_requirements/02_requirements_proposal/agents/propose_requirements.md")
        business_prompt = read("02_confirm_business_flow/01_business_flow_proposal/agents/propose_business_flow.md")
        step_prompt = read("03_confirm_step_designs/02_step_design_proposal/agents/design_steps_react.md")
        step_workflow = read("03_confirm_step_designs/02_step_design_proposal/workflow.lgwf")

        self.assertIn('"target_dir"', entry_contract)
        self.assertIn('"target_file"', entry_contract)
        self.assertIn('"target_dirs"', entry_contract)
        self.assertIn('"target_files"', entry_contract)
        self.assertIn("read_scope", entry_contract)
        self.assertIn("request.target_dir", raw_prompt)
        self.assertIn("request.target_file", raw_prompt)
        self.assertIn("workflow 目的和使用场景", raw_prompt)
        self.assertIn("creation_context_dirs", requirements_prompt)
        self.assertIn("creation_context_files", requirements_prompt)
        self.assertIn("creation_context_dirs", business_prompt)
        self.assertIn("creation_context_files", business_prompt)
        self.assertNotIn("creation_context_dirs", step_prompt)
        self.assertNotIn("creation_context_files", step_prompt)

        for workflow in (requirements_workflow, business_workflow):
            self.assertIn("TARGET_DIRS state.lgwf_wf_create.creation_context_dirs", workflow)
            self.assertIn("TARGET_FILES state.lgwf_wf_create.creation_context_files", workflow)
        self.assertNotIn("TARGET_DIRS state.lgwf_wf_create.creation_context_dirs", step_workflow)
        self.assertNotIn("TARGET_FILES state.lgwf_wf_create.creation_context_files", step_workflow)

        for text in (agents_md, readme):
            self.assertIn("执行计划", text)
            self.assertIn("不得执行", text)
        for text in (raw_prompt, requirements_prompt, business_prompt):
            self.assertIn("执行计划", text)
            self.assertIn("不作为", text)

        self.assertIn("目的、使用场景", requirements_prompt)
        self.assertIn("参考路径作为证据来源", requirements_prompt)
        self.assertIn("业务工作流", business_prompt)
        self.assertIn("结合 raw intent", business_prompt)
        self.assertIn(".lgwf/business_flow.json", step_prompt)
        self.assertNotIn(".lgwf/business_flow_proposal.json", step_prompt)
        self.assertNotIn('READ workspace file ".lgwf/business_flow_proposal.json";', step_workflow)

    def test_step_design_prompt_stays_inside_design_node_contract(self) -> None:
        prompt = read("03_confirm_step_designs/02_step_design_proposal/agents/design_steps_react.md")

        for required in (
            "不是开放式创意设计",
            "不要调用或遵循外部 brainstorming",
            "只读取本 prompt 的 Inputs",
            "不要读取 `wf/04_implement_steps_react/`",
            "不得生成 `docs/superpowers/`",
            "唯一目标是把已确认输入确定性转换",
        ):
            self.assertIn(required, prompt)

    def test_all_proposal_reviews_have_quality_gate_before_review(self) -> None:
        cases = (
            (
                "01_confirm_requirements/02_requirements_proposal/workflow.lgwf",
                "requirements_proposal_react",
                "OBSERVE PY",
                ".lgwf/create_requirements_proposal_quality_gate.json",
            ),
            (
                "02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf",
                "business_flow_proposal_react",
                "OBSERVE PY",
                ".lgwf/business_flow_proposal_quality_gate.json",
            ),
            (
                "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf",
                "step_design_proposal_react",
                "OBSERVE PY",
                ".lgwf/step_designs_proposal_quality_gate.json",
            ),
        )
        for relative, proposal_node, gate_snippet, gate_file in cases:
            workflow = read(relative)
            self.assertIn(gate_file, workflow)
            if gate_snippet == "OBSERVE PY":
                self.assertIn(f"REACT {proposal_node}", workflow)
                self.assertIn("OBSERVE PY", workflow)
                expected_validate_script = (
                    'SCRIPT "scripts/validate_step_designs_proposal.py"'
                    if proposal_node == "step_design_proposal_react"
                    else 'SCRIPT "scripts/validate_proposal.py"'
                )
                self.assertIn(expected_validate_script, workflow)
                expected_assert = (
                    "assert_requirements_proposal_quality_gate"
                    if proposal_node == "requirements_proposal_react"
                    else "assert_business_flow_proposal_quality_gate"
                    if proposal_node == "business_flow_proposal_react"
                    else "assert_step_designs_proposal_quality_gate"
                )
                self.assertRegex(workflow, rf"{proposal_node}\s+THEN\s+{expected_assert}")
            else:
                self.assertIn(f"PY {gate_snippet}", workflow)
                self.assertRegex(workflow, rf"{proposal_node}\s+THEN\s+{gate_snippet}")

        review_cases = (
            ("01_confirm_requirements/03_requirements_review/workflow.lgwf", "prepare_requirements_confirmation", "confirm_requirements"),
            ("02_confirm_business_flow/02_business_flow_review/workflow.lgwf", "prepare_business_flow_confirmation", "confirm_business_flow"),
            ("03_confirm_step_designs/03_step_design_review/workflow.lgwf", "prepare_step_design_confirmation", "confirm_step_designs"),
        )
        for relative, prepare_node, review_node in review_cases:
            workflow = read(relative)
            self.assertRegex(workflow, rf"{prepare_node}\s+THEN\s+{review_node}")

    def test_all_proposal_prompts_require_current_target_identity(self) -> None:
        for relative in (
            "01_confirm_requirements/02_requirements_proposal/agents/propose_requirements.md",
            "02_confirm_business_flow/01_business_flow_proposal/agents/propose_business_flow.md",
            "03_confirm_step_designs/02_step_design_proposal/agents/design_steps_react.md",
        ):
            prompt = read(relative)
            self.assertIn("workflow_id", prompt, relative)
            self.assertIn("target_package_root", prompt, relative)

    def test_all_codex_prompt_nodes_have_contract_boundary_coverage(self) -> None:
        expected_nodes = {
            "01_confirm_requirements/02_requirements_proposal/workflow.lgwf:act",
            "02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf:act",
            "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf:act",
            "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf:implement_current_unit",
            "04_implement_steps_react/02_observe_audit/workflow.lgwf:observe_implementation",
            "04_implement_steps_react/workflow.lgwf:reason",
        }
        found_nodes: dict[str, str] = {}
        for workflow_path in sorted(ROOT.rglob("*.lgwf")):
            relative = workflow_path.relative_to(ROOT).as_posix()
            text = workflow_path.read_text(encoding="utf-8")
            matches = list(
                re.finditer(
                    r"(?m)^(?P<indent>\s*)(?:(?:CODEX\s+(?P<node>\w+))|(?P<slot>REASON|ACT|OBSERVE|DIAGNOSE|PLAN)\s+CODEX\b)",
                    text,
                )
            )
            for index, match in enumerate(matches):
                node_name = match.group("node") or match.group("slot").lower()
                next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                found_nodes[f"{relative}:{node_name}"] = text[match.start() : next_start]

        self.assertEqual(expected_nodes, set(found_nodes))
        for node_id, block in found_nodes.items():
            self.assertIn("CONTRACT {", block, node_id)
            for output_path in re.findall(r'OUTPUT_(?:JSON|FILE)\s+"([^"]+)"', block):
                self.assertIn(f'WRITE workspace file "{output_path}"', block, node_id)

    def test_codex_output_json_files_have_schema_registry_entries(self) -> None:
        schema_path = (
            ROOT
            / "04_implement_steps_react/01_implement_units/01_implement_one_unit/resources/codex_output_schemas.json"
        )
        schemas = json.loads(schema_path.read_text(encoding="utf-8"))
        codex_schemas = schemas["codex_output_json_schemas"]
        target_schemas = schemas["target_package_output_file_schemas"]

        output_json_paths: set[str] = set()
        for workflow_path in sorted(ROOT.rglob("*.lgwf")):
            text = workflow_path.read_text(encoding="utf-8")
            output_json_paths.update(re.findall(r'OUTPUT_JSON\s+"([^"]+)"\s+AS_FILE', text))

        self.assertEqual(
            {
                ".lgwf/create_requirements_proposal.json",
                ".lgwf/business_flow_proposal.json",
                ".lgwf/step_designs_proposal.json",
                ".lgwf/current_implementation_unit_result.json",
                ".lgwf/implementation_observe.json",
            },
            output_json_paths,
        )
        self.assertEqual(output_json_paths, set(codex_schemas))
        for output_path, schema in codex_schemas.items():
            self.assertEqual("object", schema.get("type"), output_path)
            self.assertIsInstance(schema.get("required"), list, output_path)
            self.assertGreater(len(schema["required"]), 0, output_path)

        self.assertIn("entry_contract.json", target_schemas)
        self.assertIn("wf/artifact_contracts.json", target_schemas)
        self.assertIn("input_schema", target_schemas["entry_contract.json"]["required"])
        self.assertIn("delivery_artifacts", target_schemas["wf/artifact_contracts.json"]["required"])

    def test_revision_prompts_are_revision_approval_prompts(self) -> None:
        for relative in (
            "01_confirm_requirements/03_requirements_review/agents/revise_requirements.md",
            "02_confirm_business_flow/02_business_flow_review/agents/revise_business_flow.md",
            "03_confirm_step_designs/03_step_design_review/agents/revise_step_designs.md",
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
                "01_confirm_requirements/03_requirements_review/agents/confirm_requirements.md",
                "requirements_confirmation_context.review_context_json",
                "confirm_requirements",
            ),
            (
                "02_confirm_business_flow/02_business_flow_review/agents/confirm_business_flow.md",
                "business_flow_confirmation_context.review_context_json",
                "confirm_business_flow",
            ),
            (
                "03_confirm_step_designs/03_step_design_review/agents/confirm_step_designs.md",
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
        workflow = read("03_confirm_step_designs/03_step_design_review/workflow.lgwf")
        implement_workflow = read("04_implement_steps_react/workflow.lgwf")
        observe_workflow = read("04_implement_steps_react/02_observe_audit/workflow.lgwf")
        spec = read("04_implement_steps_react/agents/spec.md")
        observe_prompt = read("04_implement_steps_react/02_observe_audit/agents/observe.md")
        self.assertIn("PY prepare_implementation_context", workflow)
        self.assertRegex(workflow, r"apply_confirmed_step_designs\s+THEN\s+prepare_implementation_context")
        self.assertNotIn('READ workspace file ".lgwf/implementation_context.json";', workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_context.json";', workflow)
        self.assertIn('WORKFLOW "04_implement_steps_react/workflow.lgwf"', root_workflow)
        self.assertIn('SPEC "agents/spec.md"', implement_workflow)
        self.assertTrue((ROOT / "04_implement_steps_react/agents/spec.md").exists())
        self.assertFalse((ROOT / "03_confirm_step_designs/agents/implement_steps_react_spec.md").exists())
        self.assertIn('workspace file ".lgwf/implementation_context.json"', implement_workflow)
        self.assertIn('workspace file ".lgwf/implementation_audit_result.json"', implement_workflow)
        self.assertIn('workspace file ".lgwf/implementation_observe.json"', implement_workflow)
        self.assertIn('workspace file ".lgwf/scaffold_package_result.json"', implement_workflow)
        self.assertIn(
            'workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            implement_workflow,
        )
        self.assertIn('workspace dir ".lgwf/create_reference_context"', implement_workflow)
        self.assertNotIn('workspace dir ".lgwf/create_reference_context/dsl-assist"', implement_workflow)
        self.assertIn("target_package_abs", spec)
        self.assertIn("target_package_root` 是 `workspace_root` 相对路径", spec)
        self.assertIn("禁止从 `work_dir` 使用 `..`", spec)
        self.assertIn("OBSERVE WORKFLOW observe_audit", implement_workflow)
        self.assertIn("scripts/audit_created_package.py", observe_workflow)
        self.assertIn("CODEX observe_implementation", observe_workflow)
        self.assertIn('workflow file "agents/spec.md"', observe_workflow)
        self.assertIn('READ workflow file "agents/spec.md";', observe_workflow)
        self.assertNotIn("INSTRUCTION state.lgwf_wf_create.implementation_audit_result", observe_workflow)
        self.assertIn(".lgwf/implementation_audit_result.json", observe_workflow)
        self.assertIn(".lgwf/scaffold_package_result.json", observe_workflow)
        self.assertIn('READ workspace file ".lgwf/step_designs.json";', observe_workflow)
        self.assertIn(".lgwf/implementation_audit_result.json", observe_prompt)
        self.assertIn(".lgwf/scaffold_package_result.json", observe_prompt)
        self.assertIn('CONTEXT workflow file "agents/spec.md"', observe_prompt)
        self.assertIn("脚本 audit", observe_prompt)
        act_workflow = read("04_implement_steps_react/01_implement_units/workflow.lgwf")
        unit_workflow = read("04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf")
        unit_prompt = read("04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md")
        self.assertIn("ACT WORKFLOW implement_units", implement_workflow)
        self.assertIn('WORKFLOW "01_implement_units/workflow.lgwf"', implement_workflow)
        self.assertNotIn("ACT CODEX", implement_workflow)
        self.assertIn("FOREACH implement_each_unit", act_workflow)
        self.assertIn('WORKFLOW "01_implement_one_unit/workflow.lgwf"', act_workflow)
        self.assertNotIn('RUN_WORKFLOW "01_implement_one_unit/workflow.lgwf"', act_workflow)
        self.assertIn("RESULTS state.lgwf_wf_create.implementation_unit_results.items", act_workflow)
        self.assertIn("CODEX implement_current_unit", unit_workflow)
        self.assertIn('CONTEXT workflow file "agents/spec.md"', unit_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/current_implementation_unit_context.json"', unit_workflow)
        self.assertIn(
            'CONTEXT workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            unit_workflow,
        )
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context"', unit_workflow)
        self.assertNotIn("TARGET_DIRS state.lgwf_wf_create.current_implementation_unit_target_dirs", unit_workflow)
        self.assertNotIn("TARGET_FILES state.lgwf_wf_create.current_implementation_unit_target_files", unit_workflow)
        self.assertIn('WRITE workspace dir ".lgwf/implementation_stage";', unit_workflow)
        self.assertIn("当前 implementation unit", unit_prompt)
        self.assertIn("current_implementation_unit_context.json", unit_prompt)
        self.assertIn("workspace_output_files", unit_prompt)
        self.assertIn("stage_dir", unit_prompt)
        self.assertIn("workflow_ref", unit_prompt)

    def test_implementation_react_shared_rules_live_in_spec(self) -> None:
        spec = read("04_implement_steps_react/agents/spec.md")
        role_prompts = {
            "reason": read("04_implement_steps_react/agents/reason.md"),
            "act": read("04_implement_steps_react/01_implement_units/agents/act.md"),
            "act_unit": read("04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md"),
            "observe": read("04_implement_steps_react/02_observe_audit/agents/observe.md"),
        }

        self.assertIn("## ReAct 共同准则", spec)
        for required in (
            "`target_package_abs`",
            "`target_package_root` 是 `workspace_root` 相对路径",
            "禁止从 `work_dir` 使用 `..`",
            "`.lgwf/step_designs.json` 的结构化输入契约",
            "结构化 `step_designs[]` 条目",
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
        act_workflow = read("04_implement_steps_react/01_implement_units/workflow.lgwf")
        act_prompt = read("04_implement_steps_react/01_implement_units/agents/act.md")
        reason_block = re.search(r"REASON CODEX.*?ACT WORKFLOW", workflow, re.S)
        act_block = re.search(r"ACT WORKFLOW.*?OBSERVE WORKFLOW", workflow, re.S)
        self.assertIsNotNone(reason_block)
        self.assertIsNotNone(act_block)
        self.assertRegex(reason_block.group(0), r"TIMEOUT\s+1200")
        self.assertIn("PY prepare_implementation_units", act_workflow)
        self.assertIn("PY merge_implementation_results", act_workflow)
        self.assertIn("已存在的目标 package", act_prompt)
        self.assertIn("续写草稿", act_prompt)
        self.assertIn("先补齐缺失的必需文件", act_prompt)


if __name__ == "__main__":
    unittest.main()
