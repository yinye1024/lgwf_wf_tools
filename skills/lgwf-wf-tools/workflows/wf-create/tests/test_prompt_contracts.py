from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "wf"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def read_step_design_prompts() -> str:
    return "\n".join(
        read(relative)
        for relative in (
            "03_confirm_step_designs/02_step_design_proposal/agents/generate_step_designs.md",
            "03_confirm_step_designs/02_step_design_proposal/agents/reason_step_design_repair.md",
            "03_confirm_step_designs/02_step_design_proposal/agents/act_step_design_repair.md",
        )
    )


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
        step_prompt = read_step_design_prompts()
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
            self.assertIn("ANALYSIS_DIRS state.lgwf_wf_create.creation_context_dirs", workflow)
            self.assertIn("ANALYSIS_FILES state.lgwf_wf_create.creation_context_files", workflow)
        self.assertNotIn("ANALYSIS_DIRS state.lgwf_wf_create.creation_context_dirs", step_workflow)
        self.assertNotIn("ANALYSIS_FILES state.lgwf_wf_create.creation_context_files", step_workflow)

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
        self.assertIn("已确认业务流", step_prompt)
        self.assertNotIn(".lgwf/business_flow_proposal.json", step_prompt)
        self.assertNotIn('READ workspace file ".lgwf/business_flow_proposal.json";', step_workflow)

    def test_step_design_prompt_stays_inside_design_node_contract(self) -> None:
        prompt = read_step_design_prompts()

        for required in (
            "读取范围限定",
            "输出范围限定",
            "file_designs",
            "directory_designs",
            "workflow_id",
            "已确认输入",
        ):
            self.assertIn(required, prompt)
        reason_prompt = read(
            "03_confirm_step_designs/02_step_design_proposal/agents/reason_step_design_repair.md"
        )
        act_prompt = read(
            "03_confirm_step_designs/02_step_design_proposal/agents/act_step_design_repair.md"
        )
        proposal_workflow = read("03_confirm_step_designs/02_step_design_proposal/workflow.lgwf")
        self.assertIn("reason_feedback", reason_prompt)
        self.assertIn("step_design_observation", reason_prompt)
        self.assertIn("repair_plan", act_prompt)
        self.assertIn("读取范围限定为 runtime 提供的 `CONTEXT`", act_prompt)
        self.assertIn("DECIDE PY", proposal_workflow)
        self.assertNotIn("CODEX decide_step_designs", proposal_workflow)

    def test_proposal_reviews_have_expected_quality_or_review_boundary(self) -> None:
        cases = (
            (
                "01_confirm_requirements/02_requirements_proposal/workflow.lgwf",
                "requirements_proposal_react",
                "OBSERVE PY",
                ".lgwf/create_requirements_proposal_quality_gate.json",
            ),
            (
                "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf",
                "repair_step_designs_proposal",
                "OBSERVE PY",
                ".lgwf/step_design_observation.json",
            ),
        )
        for relative, proposal_node, gate_snippet, gate_file in cases:
            workflow = read(relative)
            self.assertIn(gate_file, workflow)
            if gate_snippet == "OBSERVE PY":
                self.assertIn(f"REACT {proposal_node}", workflow)
                self.assertIn("OBSERVE PY", workflow)
                if proposal_node == "requirements_proposal_react":
                    self.assertIn('SCRIPT "scripts/validate_proposal.py"', workflow)
                else:
                    self.assertIn('SCRIPT "scripts/validate_step_designs_structure.py"', workflow)
                expected_assert = (
                    "assert_requirements_proposal_quality_gate"
                    if proposal_node == "requirements_proposal_react"
                    else "assert_step_designs_proposal_quality_gate"
                )
                self.assertRegex(workflow, rf"{proposal_node}\s+THEN\s+{expected_assert}")
            else:
                self.assertIn(gate_snippet, workflow)

        business_workflow = read("02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf")
        self.assertIn("PY prepare_business_flow_context", business_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/business_flow_proposal_context.json"', business_workflow)
        self.assertIn("CODEX propose_business_flow", business_workflow)
        self.assertIn('OUTPUT_JSON ".lgwf/business_flow_proposal.json" AS_FILE', business_workflow)
        self.assertNotIn("REACT business_flow_proposal_react", business_workflow)
        self.assertNotIn("business_flow_proposal_quality_gate", business_workflow)

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
        ):
            prompt = read(relative)
            self.assertIn("workflow_id", prompt, relative)
            self.assertIn("target_package_root", prompt, relative)
        step_prompt = read_step_design_prompts()
        self.assertIn("workflow_id", step_prompt)
        self.assertIn("target_package_root", step_prompt)

    def test_all_codex_prompt_nodes_have_contract_boundary_coverage(self) -> None:
        expected_nodes = {
            "01_confirm_requirements/02_requirements_proposal/workflow.lgwf:act",
            "02_confirm_business_flow/01_business_flow_proposal/workflow.lgwf:propose_business_flow",
            "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf:reason",
            "03_confirm_step_designs/02_step_design_proposal/workflow.lgwf:act",
            "04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf:implement_current_unit",
            "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf:reason_repair",
            "04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf:act_repair",
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
                ".lgwf/step_design_repair_plan.json",
                ".lgwf/current_implementation_unit_result.json",
                ".lgwf/implementation_repair_reason.json",
                ".lgwf/implementation_repair_result.json",
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
        self.assertIn("wf/*/artifact_contracts.json", target_schemas)
        self.assertIn("input_schema", target_schemas["entry_contract.json"]["required"])
        self.assertIn("delivery_artifacts", target_schemas["wf/artifact_contracts.json"]["required"])
        self.assertIn("bootstrap_inputs", target_schemas["wf/*/artifact_contracts.json"]["required"])

    def test_revision_prompts_keep_review_boundaries(self) -> None:
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
        repair_workflow = read("04_implement_steps_react/02_repair_implementation_react/workflow.lgwf")
        repair_reason_workflow = read(
            "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/workflow.lgwf"
        )
        observe_workflow = read(
            "04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf"
        )
        spec = read("04_implement_steps_react/02_repair_implementation_react/agents/spec.md")
        self.assertIn("PY prepare_implementation_context", workflow)
        self.assertRegex(workflow, r"apply_confirmed_step_designs\s+THEN\s+prepare_implementation_context")
        self.assertNotIn('READ workspace file ".lgwf/implementation_context.json";', workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_context.json";', workflow)
        self.assertIn('WORKFLOW "04_implement_steps_react/workflow.lgwf"', root_workflow)
        self.assertNotIn("REACT implement_steps_react", implement_workflow)
        self.assertIn('WORKFLOW "01_implement_units/workflow.lgwf"', implement_workflow)
        self.assertIn('WORKFLOW "02_repair_implementation_react/workflow.lgwf"', implement_workflow)
        self.assertRegex(implement_workflow, r"implement_initial_units\s+THEN\s+repair_implementation")
        self.assertFalse((ROOT / "04_implement_steps_react/agents/spec.md").exists())
        self.assertFalse((ROOT / "04_implement_steps_react/agents/reason.md").exists())
        self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
        self.assertIn("REASON WORKFLOW reason_repair", repair_workflow)
        self.assertIn("ACT WORKFLOW act_repair", repair_workflow)
        self.assertIn("OBSERVE WORKFLOW observe_repair", repair_workflow)
        self.assertIn("DECIDE WORKFLOW decide_repair", repair_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/implementation_audit_result.json"', repair_reason_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/implementation_observe.json"', repair_reason_workflow)
        for forbidden in (
            ".lgwf/create_reference_context",
            ".lgwf/implementation_context.json",
            ".lgwf/implementation_result.json",
            ".lgwf/scaffold_package_result.json",
            ".lgwf/step_designs.json",
        ):
            self.assertNotIn(forbidden, repair_reason_workflow)
        self.assertIn('SPEC "agents/spec.md"', repair_workflow)
        self.assertIn('WORKFLOW "03_observe_repair/workflow.lgwf"', repair_workflow)
        self.assertTrue((ROOT / "04_implement_steps_react/02_repair_implementation_react/agents/spec.md").exists())
        self.assertFalse((ROOT / "03_confirm_step_designs/agents/implement_steps_react_spec.md").exists())
        self.assertIn('workspace file ".lgwf/implementation_context.json"', implement_workflow)
        self.assertIn('workspace file ".lgwf/implementation_audit_result.json"', implement_workflow)
        self.assertNotIn('workspace file ".lgwf/implementation_observe.json"', implement_workflow)
        self.assertNotIn('workspace file ".lgwf/implementation_decision.json"', implement_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_audit_result.json";', repair_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_observe.json";', repair_workflow)
        self.assertIn('WRITE workspace file ".lgwf/implementation_decision.json";', repair_workflow)
        self.assertNotIn('workspace file ".lgwf/scaffold_package_result.json"', implement_workflow)
        self.assertNotIn(
            'workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            implement_workflow,
        )
        self.assertNotIn('workspace dir ".lgwf/create_reference_context"', implement_workflow)
        self.assertNotIn('workspace dir ".lgwf/create_reference_context/dsl-assist"', implement_workflow)
        self.assertIn("target_package_abs", spec)
        self.assertIn("target_package_root` 是 `workspace_root` 相对路径", spec)
        self.assertIn("禁止从 `work_dir` 使用 `..`", spec)
        self.assertIn("PY audit_current_implementation", observe_workflow)
        self.assertIn("scripts/audit_current_implementation.py", observe_workflow)
        self.assertNotIn("CODEX observe_repair", observe_workflow)
        self.assertNotIn('workflow file "agents/spec.md"', observe_workflow)
        self.assertNotIn('READ workflow file "agents/spec.md";', observe_workflow)
        self.assertNotIn("INSTRUCTION state.lgwf_wf_create.implementation_audit_result", observe_workflow)
        self.assertIn(".lgwf/implementation_audit_result.json", observe_workflow)
        self.assertNotIn(".lgwf/scaffold_package_result.json", observe_workflow)
        self.assertIn('READ workspace file ".lgwf/step_designs.json";', observe_workflow)
        act_workflow = read("04_implement_steps_react/01_implement_units/workflow.lgwf")
        unit_workflow = read("04_implement_steps_react/01_implement_units/01_implement_one_unit/workflow.lgwf")
        unit_prompt = read("04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md")
        self.assertIn('WORKFLOW "01_implement_units/workflow.lgwf"', implement_workflow)
        self.assertNotIn("ACT CODEX", implement_workflow)
        self.assertIn("FOREACH implement_each_unit", act_workflow)
        self.assertIn('WORKFLOW "01_implement_one_unit/workflow.lgwf"', act_workflow)
        self.assertNotIn('RUN_WORKFLOW "01_implement_one_unit/workflow.lgwf"', act_workflow)
        self.assertIn("RESULTS state.lgwf_wf_create.implementation_unit_results.items", act_workflow)
        self.assertNotIn("CODEX prime_implementation_codex", act_workflow)
        self.assertNotIn('PROMPT "agents/prime_implementation_codex.md"', act_workflow)
        self.assertNotIn('KEEP_SESSION KEY "implementation_codex"', act_workflow)
        self.assertRegex(
            act_workflow,
            r"prepare_implementation_units\s+THEN\s+implement_each_unit",
        )
        self.assertIn("CODEX implement_current_unit", unit_workflow)
        prepare_block = unit_workflow.split("CODEX implement_current_unit", 1)[0]
        implement_block = unit_workflow.split("CODEX implement_current_unit", 1)[1].split(
            "PY publish_current_implementation_unit_result",
            1,
        )[0]
        self.assertNotIn('CONTEXT workflow file "agents/spec.md"', unit_workflow)
        self.assertNotIn('READ workflow file "agents/spec.md";', unit_workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/current_implementation_unit_context.json"', implement_block)
        self.assertNotIn(
            'CONTEXT workspace file ".lgwf/create_reference_context/implementation-reference-index.md"',
            implement_block,
        )
        self.assertNotIn('CONTEXT workspace dir ".lgwf/create_reference_context"', implement_block)
        self.assertNotIn('KEEP_SESSION KEY "implementation_codex"', implement_block)
        self.assertNotIn('READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";', prepare_block)
        self.assertNotIn('READ workspace dir ".lgwf/create_reference_context";', prepare_block)
        self.assertNotIn(
            'READ workspace file ".lgwf/create_reference_context/implementation-reference-index.md";',
            implement_block,
        )
        self.assertNotIn('READ workspace dir ".lgwf/create_reference_context";', implement_block)
        self.assertNotIn("TARGET_DIRS state.lgwf_wf_create.current_implementation_unit_target_dirs", unit_workflow)
        self.assertNotIn("TARGET_FILES state.lgwf_wf_create.current_implementation_unit_target_files", unit_workflow)
        self.assertIn('WRITE workspace dir ".lgwf/implementation_stage";', unit_workflow)
        self.assertIn("当前 implementation unit", unit_prompt)
        self.assertIn("current_implementation_unit_context.json", unit_prompt)
        self.assertIn("workspace_output_files", unit_prompt)
        self.assertIn("target_output_file_schemas", unit_prompt)
        self.assertNotIn("implementation_reference_context", unit_prompt)
        self.assertNotIn("implementation-reference-index.md", unit_prompt)
        self.assertNotIn("lgwf_dsl_contract", unit_prompt)
        self.assertNotIn("resources/lgwf_dsl_authoring.md", unit_prompt)
        self.assertNotIn('CONTEXT workflow file "resources/lgwf_dsl_authoring.md"', implement_block)
        self.assertNotIn('READ workflow file "resources/lgwf_dsl_authoring.md";', implement_block)
        self.assertNotIn('KEEP_SESSION KEY "implementation_codex"', unit_prompt)
        self.assertNotIn("prime_implementation_codex", unit_prompt)
        self.assertIn("exact_content", unit_prompt)
        self.assertIn("不得执行 `rg ... .lgwf`", unit_prompt)
        self.assertNotIn("agents/spec.md", unit_prompt)
        self.assertIn("stage_dir", unit_prompt)
        self.assertIn("workflow_ref", unit_prompt)

    def test_repair_react_shared_rules_live_in_repair_spec(self) -> None:
        spec = read("04_implement_steps_react/02_repair_implementation_react/agents/spec.md")
        duplicate_specs = (
            "04_implement_steps_react/agents/spec.md",
            "04_implement_steps_react/agents/reason.md",
            "04_implement_steps_react/01_implement_units/agents/spec.md",
            "04_implement_steps_react/01_implement_units/agents/act.md",
            "04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/spec.md",
            "04_implement_steps_react/02_observe_audit",
            "04_implement_steps_react/README.md",
            "04_implement_steps_react/01_implement_units/README.md",
            "04_implement_steps_react/01_implement_units/01_implement_one_unit/README.md",
            "04_implement_steps_react/02_repair_implementation_react/README.md",
        )
        for relative in duplicate_specs:
            self.assertFalse((ROOT / relative).exists(), relative)
        role_prompts = {
            "reason_repair": read(
                "04_implement_steps_react/02_repair_implementation_react/01_reason_repair/agents/reason_repair.md"
            ),
        }
        local_prompts = {
            "act_unit": read("04_implement_steps_react/01_implement_units/01_implement_one_unit/agents/act_unit.md"),
            "act_repair": read(
                "04_implement_steps_react/02_repair_implementation_react/02_act_repair/agents/act_repair.md"
            ),
        }
        observe_workflow = read("04_implement_steps_react/02_repair_implementation_react/03_observe_repair/workflow.lgwf")
        decide_workflow = read("04_implement_steps_react/02_repair_implementation_react/04_decide_repair/workflow.lgwf")

        self.assertIn("## ReAct 共同准则", spec)
        for required in (
            "Python audit 反馈",
            "Python 检查失败",
            "`target_package_abs`",
            "`target_package_root` 是 `workspace_root` 相对路径",
            "禁止从 `work_dir` 使用 `..`",
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

        for name, prompt in local_prompts.items():
            self.assertNotIn("`agents/spec.md`", prompt, name)
        self.assertIn("只能读 `.lgwf/current_implementation_unit_context.json`", local_prompts["act_unit"])
        self.assertIn("只能写 `workspace_output_files`", local_prompts["act_unit"])
        self.assertIn("schema 只来自 `target_output_file_schemas`", local_prompts["act_unit"])
        self.assertIn("不递归读 `.lgwf`", local_prompts["act_unit"])
        self.assertNotIn("implementation_reference_context", local_prompts["act_unit"])
        self.assertNotIn("implementation-reference-index.md", local_prompts["act_unit"])
        self.assertNotIn("lgwf_dsl_contract", local_prompts["act_unit"])
        self.assertNotIn("resources/lgwf_dsl_authoring.md", local_prompts["act_unit"])
        self.assertIn("exact_content", local_prompts["act_unit"])
        self.assertIn("只能写 `.lgwf/implementation_repair_stage/<target_file>`", local_prompts["act_repair"])
        self.assertIn("`target_package_root` 下 `target_files`", local_prompts["act_repair"])
        self.assertIn("原始 Python audit 结果", role_prompts["reason_repair"])
        self.assertIn("`target_package_root` 原样写入输出", role_prompts["reason_repair"])
        self.assertIn("PY audit_current_implementation", observe_workflow)
        self.assertNotIn("CODEX observe_repair", observe_workflow)
        self.assertIn("PY write_repair_decision", decide_workflow)
        self.assertNotIn("CODEX decide_repair", decide_workflow)

    def test_implementation_act_is_resumable_and_not_bound_to_default_timeout(self) -> None:
        workflow = read("04_implement_steps_react/workflow.lgwf")
        act_workflow = read("04_implement_steps_react/01_implement_units/workflow.lgwf")
        repair_workflow = read("04_implement_steps_react/02_repair_implementation_react/workflow.lgwf")
        act_repair_workflow = read("04_implement_steps_react/02_repair_implementation_react/02_act_repair/workflow.lgwf")
        self.assertIn("STEP implement_initial_units", workflow)
        self.assertIn("STEP repair_implementation", workflow)
        self.assertIn("REACT repair_implementation_react MAX 3", repair_workflow)
        self.assertIn("TIMEOUT 1200", act_repair_workflow)
        self.assertIn("PY prepare_implementation_units", act_workflow)
        self.assertNotIn("CODEX prime_implementation_codex", act_workflow)
        self.assertIn("PY merge_implementation_results", act_workflow)


if __name__ == "__main__":
    unittest.main()
