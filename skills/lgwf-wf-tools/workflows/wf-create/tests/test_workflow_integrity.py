from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROOT = PACKAGE_ROOT / "wf"
sys.dont_write_bytecode = True


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class WorkflowCreateIntegrityTest(unittest.TestCase):
    def test_all_workflow_resource_references_exist(self) -> None:
        patterns = (
            r'WORKFLOW "([^"]+)"',
            r'PROMPT "([^"]+)"',
            r'PROMPT_REF "([^"]+)"',
            r'SCRIPT "([^"]+)"',
        )
        for workflow in ROOT.rglob("workflow.lgwf"):
            text = workflow.read_text(encoding="utf-8")
            for pattern in patterns:
                for relative in re.findall(pattern, text):
                    with self.subTest(workflow=workflow.relative_to(ROOT).as_posix(), relative=relative):
                        self.assertFalse(Path(relative).is_absolute())
                        self.assertNotIn("..", Path(relative).parts)
                        self.assertTrue((workflow.parent / relative).exists(), relative)

    def test_sub_approval_workflows_have_persist_and_decision_routes(self) -> None:
        expectations = (
            (
                "01_confirm_requirements/workflow.lgwf",
                "confirm_requirements",
                "apply_confirmed_requirements",
                ".lgwf/create_requirements_approval.json",
            ),
            (
                "02_confirm_business_flow/workflow.lgwf",
                "confirm_business_flow",
                "apply_confirmed_business_flow",
                ".lgwf/business_flow_approval.json",
            ),
            (
                "03_confirm_step_designs/workflow.lgwf",
                "confirm_step_designs",
                "apply_confirmed_step_designs",
                ".lgwf/step_design_confirmation_record.json",
            ),
        )
        for relative, approval, apply_node, persist in expectations:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(f"REVIEW {approval}", text)
            self.assertIn('OPTIONS ["approve", "revise", "reject"]', text)
            self.assertIn(f'PERSIST "{persist}"', text)
            self.assertIn("FLOW {", text)
            self.assertIn(approval, text)
            self.assertIn(f'WHEN "approve" THEN {apply_node}', text)
            self.assertIn(f'WHEN "revise" THEN {approval}', text)
            self.assertIn('WHEN "reject" THEN FAIL_ALL', text)

    def test_raw_intent_approval_is_persisted_without_decision_routing(self) -> None:
        text = (ROOT / "01_confirm_requirements/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('PERSIST ".lgwf/raw_intent_request.json"', text)
        self.assertIn("APPROVAL collect_raw_intent", text)
        self.assertIn("collect_raw_intent", text)
        self.assertIn("THEN finish_raw_intent", text)

    def test_apply_scripts_reject_non_approve_decisions(self) -> None:
        cases = (
            ("01_confirm_requirements/scripts/apply_confirmed_requirements.py", "create_requirements_approval.json", "create_requirements.json"),
            ("02_confirm_business_flow/scripts/apply_confirmed_business_flow.py", "business_flow_approval.json", "business_flow.json"),
            ("03_confirm_step_designs/scripts/apply_confirmed_step_designs.py", "step_design_confirmation_record.json", "step_designs.json"),
        )
        for relative, approval_name, output_name in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"decision": "revise", "target_package_root": "skills/demo"}),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    module.write_confirmed_artifact(root)
                self.assertFalse((lgwf_dir / output_name).exists())

    def test_apply_scripts_use_fixed_proposal_after_approved_revision(self) -> None:
        cases = (
            (
                "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
                "create_requirements_approval.json",
                "create_requirements_revision_approval.json",
                "create_requirements_proposal.json",
                "create_requirements.json",
                {"workflow_name": "demo", "target_package_root": "skills/demo"},
            ),
            (
                "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
                "business_flow_approval.json",
                "business_flow_revision_approval.json",
                "business_flow_proposal.json",
                "business_flow.json",
                {"workflow_name": "demo", "stages": [{"stage_id": "scaffold"}]},
            ),
            (
                "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_design_revision_approval.json",
                "step_designs_proposal.json",
                "step_designs.json",
                {"step_designs": [{"step_slug": "scaffold"}]},
            ),
        )
        for relative, approval_name, revision_name, proposal_name, output_name, confirmed in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_revision"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / proposal_name).write_text(json.dumps(confirmed), encoding="utf-8")
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"decision": "revise", "changes": ["local change"]}),
                    encoding="utf-8",
                )
                (lgwf_dir / revision_name).write_text(
                    json.dumps(
                        {
                            "decision": "approve",
                            "confirmed": {"approval": "approve", "route": "approve"},
                        }
                    ),
                    encoding="utf-8",
                )
                result = module.write_confirmed_artifact(root)
                artifact = next(value for value in result.values() if isinstance(value, dict) and "artifact_path" in value)
                self.assertEqual(artifact["artifact_path"], f".lgwf/{output_name}")
                self.assertEqual(artifact["source_approval_file"], f".lgwf/{revision_name}")
                self.assertEqual(artifact["confirmed"], confirmed)
                self.assertNotIn("approval", artifact)

    def test_apply_scripts_reject_missing_fixed_proposal(self) -> None:
        cases = (
            (
                "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
                "create_requirements_approval.json",
                "create_requirements_revision_approval.json",
                "create_requirements.json",
            ),
            (
                "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
                "business_flow_approval.json",
                "business_flow_revision_approval.json",
                "business_flow.json",
            ),
            (
                "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
                "step_design_confirmation_record.json",
                "step_design_revision_approval.json",
                "step_designs.json",
            ),
        )
        for relative, approval_name, revision_name, output_name in cases:
            module = load_module(ROOT / relative, relative.replace("/", "_approval_field"))
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                lgwf_dir = root / ".lgwf"
                lgwf_dir.mkdir()
                (lgwf_dir / approval_name).write_text(
                    json.dumps({"approval": "revise", "changes": ["local change"]}),
                    encoding="utf-8",
                )
                (lgwf_dir / revision_name).write_text(
                    json.dumps({"approval": "approve"}),
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    module.write_confirmed_artifact(root)
                self.assertFalse((lgwf_dir / output_name).exists())

    def test_confirmed_runtime_artifacts_are_reported_separately_from_source_files(self) -> None:
        summary_module = load_module(
            ROOT / "06_summarize_create_result/scripts/summarize_create_result.py",
            "summary_integrity",
        )
        summary = summary_module.build_summary({})
        self.assertIn(".lgwf/create_requirements.json", summary["runtime_artifacts"])
        self.assertIn(".lgwf/business_flow.json", summary["runtime_artifacts"])
        self.assertIn(".lgwf/step_designs.json", summary["runtime_artifacts"])
        self.assertNotIn(".lgwf/create_requirements.json", summary["produced_files"])

    def test_apply_scripts_share_common_confirmation_helpers(self) -> None:
        for relative in (
            "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
            "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
            "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("from confirmation_io import", text)
            self.assertIn("shared", text)

    def test_step_design_and_implementation_use_dsl_assist_context(self) -> None:
        parent_workflow = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY prepare_dsl_reference_context", parent_workflow)
        self.assertIn("prepare_dsl_reference_context THEN design_steps_react", parent_workflow)
        contracts = json.loads((ROOT / "artifact_contracts.json").read_text(encoding="utf-8"))
        script_writes = contracts["script_writes"]["prepare_dsl_reference_context"]

        text = (ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context/dsl-assist"', text)
        self.assertIn('CONTEXT workspace dir ".lgwf/create_reference_context/workflow-modular-development"', text)
        for _ in (0,):
            for reference in (
                ".lgwf/create_reference_context/dsl-assist/guide.md",
                ".lgwf/create_reference_context/dsl-assist/create-workflow.md",
                ".lgwf/create_reference_context/dsl-assist/workflow-audit-checklist.md",
                ".lgwf/create_reference_context/workflow-modular-development/LGWF_WF_MODULAR_DEVELOPMENT.md",
                ".lgwf/create_reference_context/module-contract/module-contract.md",
            ):
                self.assertIn(reference, script_writes)

    def test_docs_no_longer_describe_confirmed_artifacts_as_future_only(self) -> None:
        stale_patterns = (
            "未来确认后固化接口",
            "不是当前 run 必需产物",
            "当前阶段不要求也不生成 `.lgwf/create_requirements.json`",
            "当前 run 不要求生成 `.lgwf/step_designs.json`",
        )
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for pattern in stale_patterns:
                self.assertNotIn(pattern, text, path.as_posix())

    def test_scaffold_plan_includes_confirmation_apply_scripts(self) -> None:
        module = load_module(
            ROOT / "02_confirm_business_flow/scripts/scaffold_package.py",
            "scaffold_integrity",
        )
        plan = module.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "business_flow": {"stages": []},
            }
        )
        for relative in (
            "wf/01_confirm_requirements/scripts/apply_confirmed_requirements.py",
            "wf/02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
            "wf/03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
            "wf/shared/scripts/confirmation_io.py",
            "wf/shared/scripts/review_context.py",
        ):
            self.assertIn(relative, plan["create_files"])
        self.assertNotIn("wf/common/confirmation_io.py", plan["create_files"])

    def test_summary_workflow_uses_py_result_and_script_writes_json(self) -> None:
        workflow = (ROOT / "06_summarize_create_result/workflow.lgwf").read_text(encoding="utf-8")
        script = (ROOT / "06_summarize_create_result/scripts/summarize_create_result.py").read_text(encoding="utf-8")
        self.assertNotIn("OUTPUT_JSON", workflow)
        self.assertIn("RESULT state.lgwf_wf_create.summary_result", workflow)
        self.assertIn("create_result_summary.json", script)

    def test_created_package_validation_runs_before_summary_and_handoff(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY validate_created_package", workflow)
        self.assertIn('STEP enrich_contracts_react', workflow)
        self.assertIn('WORKFLOW "05_enrich_contracts_react/workflow.lgwf"', workflow)
        self.assertIn(
            "THEN implement_draft\n"
            "  THEN implement_steps_react\n"
            "  THEN enrich_contracts_react\n"
            "  THEN validate_created_package\n"
            "  THEN summarize_create_result",
            workflow,
        )
        self.assertIn('SCRIPT "scripts/validate_created_package.py"', workflow)

    def test_contract_enrichment_react_runs_audit_before_final_validation(self) -> None:
        workflow = (ROOT / "05_enrich_contracts_react/workflow.lgwf").read_text(encoding="utf-8")
        observe_workflow = (ROOT / "05_enrich_contracts_react/observe_audit.lgwf").read_text(encoding="utf-8")
        spec = (ROOT / "05_enrich_contracts_react/agents/spec.md").read_text(encoding="utf-8")
        act_prompt = (ROOT / "05_enrich_contracts_react/agents/act.md").read_text(encoding="utf-8")

        self.assertIn("REACT enrich_contracts_react MAX 3", workflow)
        self.assertIn('SPEC "agents/spec.md"', workflow)
        self.assertIn('workspace file ".lgwf/create_reference_context/module-contract/module-contract.md"', workflow)
        self.assertIn('WORKFLOW "observe_audit.lgwf"', workflow)
        self.assertIn('OUTPUT_JSON ".lgwf/contract_enrichment_result.json"', workflow)
        self.assertIn('WRITE workspace file ".lgwf/contract_reason.md"', workflow)
        self.assertIn('WRITE workspace file ".lgwf/contract_enrichment_result.json"', workflow)
        self.assertIn('WRITE workspace file ".lgwf/contract_observe.json"', workflow)
        self.assertIn('SCRIPT "scripts/audit_contract_package.py"', observe_workflow)
        audit_script = (ROOT / "05_enrich_contracts_react/scripts/audit_contract_package.py").read_text(encoding="utf-8")
        self.assertIn("lgwf.py audit", audit_script)
        self.assertIn("module-contract.md", spec)
        self.assertIn("模块定位", act_prompt)
        self.assertIn("入口", act_prompt)
        self.assertIn("依赖", act_prompt)
        self.assertIn("状态边界", act_prompt)
        self.assertIn("产物", act_prompt)
        self.assertIn("验证", act_prompt)
        self.assertIn("禁止事项", act_prompt)
        for required in (
            "扫描目标 package 下所有 `workflow.lgwf`",
            "为所有节点逐个生成或补齐 `CONTRACT`",
            "`OUTPUT_JSON`、`OUTPUT_FILE` 和 `PERSIST` 必须有同节点 `CONTRACT WRITE workspace file`",
            "不要把节点内部临时文件、scratch 文件或 helper 缓存写入 `CONTRACT`",
            "CONTRACT 合法落点",
            "STEP <id> WORKFLOW",
            "REACT slot",
            "不得生成 `STEP <id> CONTRACT",
        ):
            self.assertIn(required, spec)
        for required in (
            "建立逐节点契约清单",
            "逐个节点说明应声明的 `CONTRACT READ` 和 `CONTRACT WRITE`",
            "扫描 prompt、script、`OUTPUT_JSON`、`OUTPUT_FILE`、`PERSIST` 和上下游文件引用",
            "确认每个待补 `CONTRACT` 的合法落点",
        ):
            self.assertIn(required, (ROOT / "05_enrich_contracts_react/agents/reason.md").read_text(encoding="utf-8"))
        for required in (
            "逐个修改目标 package 内所有 `workflow.lgwf`",
            "为每个有外部业务文件 I/O 的节点补齐 `CONTRACT`",
            "`CONTRACT` 只声明节点外部业务文件输入输出",
            "按节点类型把 `CONTRACT` 放到 parser 接受的位置",
        ):
            self.assertIn(required, act_prompt)

    def test_agents_doc_names_route_back_to_facade_when_out_of_scope(self) -> None:
        text = (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for workflow_id in ("wf-fix", "wf-prompt-fix", "wf-prompt-upgrade", "e2e-test-generator"):
            self.assertIn(workflow_id, text)
        self.assertIn("回到 facade 路由", text)


if __name__ == "__main__":
    unittest.main()
