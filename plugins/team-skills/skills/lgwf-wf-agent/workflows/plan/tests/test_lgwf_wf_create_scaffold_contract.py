from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
PACKAGE_ROOT = ROOT / "plugins" / "team-skills" / "skills" / "lgwf-wf-create"
STEP_DIRS = (
    "00_collect_raw_intent",
    "01_propose_requirements_react",
    "02_confirm_requirements",
    "03_propose_business_flow_react",
    "04_confirm_business_flow",
    "05_scaffold_package",
    "06_design_steps_react",
    "07_confirm_step_designs",
    "08_implement_steps_react",
    "09_summarize_create_result",
)
PRIVATE_SLOT_NAMES = ("agents", "scripts", "resources", "tests")


class WorkflowCreateFoundationContractTest(unittest.TestCase):
    def test_package_entry_files_exist(self) -> None:
        for name in ("SKILL.md", "README.md", "workflow.lgwf"):
            self.assertTrue((PACKAGE_ROOT / name).is_file(), name)

    def test_package_core_dirs_exist(self) -> None:
        for relative in ("agents", "scripts", "shared", "docs/steps", "tests", "ws"):
            self.assertTrue((PACKAGE_ROOT / relative).is_dir(), relative)
        for step_dir in STEP_DIRS:
            self.assertTrue((PACKAGE_ROOT / step_dir).is_dir(), step_dir)

    def test_each_step_dir_has_private_resource_slot(self) -> None:
        for step_dir in STEP_DIRS:
            root = PACKAGE_ROOT / step_dir
            present = [name for name in PRIVATE_SLOT_NAMES if (root / name).is_dir()]
            self.assertTrue(present, f"{step_dir} 缺少私有资源位点")
            files = [path for path in root.rglob("*") if path.is_file()]
            self.assertTrue(files, f"{step_dir} 不应为空壳目录")

    def test_workflow_stage_order_and_relative_paths(self) -> None:
        text = (PACKAGE_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("..", text)
        self.assertIsNone(re.search(r"[A-Za-z]:\\\\", text))
        self.assertIsNone(re.search(r"\b(?:https?|file)://", text))

        expected_fragments = (
            'WORKFLOW "00_collect_raw_intent/workflow.lgwf"',
            'WORKFLOW "01_propose_requirements_react/workflow.lgwf"',
            'WORKFLOW "02_confirm_requirements/workflow.lgwf"',
            'WORKFLOW "03_propose_business_flow_react/workflow.lgwf"',
            'WORKFLOW "04_confirm_business_flow/workflow.lgwf"',
            'WORKFLOW "05_scaffold_package/workflow.lgwf"',
            'WORKFLOW "06_design_steps_react/workflow.lgwf"',
            'WORKFLOW "07_confirm_step_designs/workflow.lgwf"',
            'WORKFLOW "08_implement_steps_react/workflow.lgwf"',
            'WORKFLOW "09_summarize_create_result/workflow.lgwf"',
        )
        for fragment in expected_fragments:
            self.assertIn(fragment, text)

        ordered_names = (
            "collect_raw_intent",
            "propose_requirements_react",
            "confirm_requirements",
            "propose_business_flow_react",
            "confirm_business_flow",
            "scaffold_package",
            "design_steps_react",
            "confirm_step_designs",
            "implement_steps_react",
            "summarize_create_result",
        )
        last_index = -1
        for name in ordered_names:
            index = text.index(name)
            self.assertGreater(index, last_index, name)
            last_index = index

    def test_docs_define_scope_and_ws_boundary(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
            )
        )
        for text in (
            "第一版",
            "workflow 初稿",
            "ws/.lgwf",
            "不接入 `lgwf-wf-prompt-fix`",
            "不接入 `lgwf-wf-agent`",
            "UTF-8",
            "中文",
        ):
            self.assertIn(text, combined)

    def test_package_has_no_runtime_pollution(self) -> None:
        forbidden = {".tmp", "__pycache__", ".lgwf"}
        for path in PACKAGE_ROOT.rglob("*"):
            self.assertNotIn(path.name, forbidden, path)

    def test_collect_raw_intent_accepts_raw_intent_instead_of_full_json(self) -> None:
        workflow = (PACKAGE_ROOT / "00_collect_raw_intent" / "workflow.lgwf").read_text(encoding="utf-8")
        prompt = (PACKAGE_ROOT / "00_collect_raw_intent" / "confirm_raw_intent.md").read_text(encoding="utf-8")
        resource_doc = (PACKAGE_ROOT / "00_collect_raw_intent" / "resources" / "README.md").read_text(encoding="utf-8")

        self.assertIn("APPROVAL confirm_raw_intent", workflow)
        self.assertIn("原始意图", prompt)
        self.assertIn("不要求", prompt)
        self.assertIn("完整结构化 JSON", prompt)
        self.assertIn("raw_intent", resource_doc)
        self.assertIn("create_requirements_proposal", resource_doc)

    def test_requirements_proposal_prompt_defines_stable_fields_and_rationale(self) -> None:
        prompt = (PACKAGE_ROOT / "01_propose_requirements_react" / "agents" / "act.md").read_text(encoding="utf-8")
        for text in (
            "workflow_name",
            "target_package_root",
            "purpose",
            "target_users",
            "expected_inputs",
            "expected_outputs",
            "human_approval_points",
            "workflow_shape",
            "proposal_notes",
            "design_rationale",
            "JSON",
            "不得生成 `.lgwf/create_requirements.json`",
        ):
            self.assertIn(text, prompt)

    def test_confirm_requirements_template_covers_three_decisions(self) -> None:
        prompt = (PACKAGE_ROOT / "02_confirm_requirements" / "confirm_requirements.md").read_text(encoding="utf-8")
        resource_doc = (PACKAGE_ROOT / "02_confirm_requirements" / "resources" / "README.md").read_text(encoding="utf-8")
        for text in (
            "\"decision\": \"approve\"",
            "\"decision\": \"revise\"",
            "\"decision\": \"reject\"",
            "changes",
            "reason",
            "create_requirements_approval",
            "confirm 后固化",
            "当前 run 不生成 `.lgwf/create_requirements.json`",
        ):
            self.assertIn(text, prompt + "\n" + resource_doc)

    def test_requirements_boundary_docs_do_not_require_confirmed_json(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "01_propose_requirements_react" / "agents" / "act.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "02_confirm_requirements" / "confirm_requirements.md").read_text(encoding="utf-8"),
            )
        )
        self.assertIn("proposal", combined)
        self.assertIn("approval", combined)
        self.assertIn("确认后固化", combined)
        self.assertNotIn("当前 run 必须生成 `.lgwf/create_requirements.json`", combined)

    def test_business_flow_prompt_defines_stable_stage_and_dependency_contract(self) -> None:
        prompt = (PACKAGE_ROOT / "03_propose_business_flow_react" / "agents" / "act.md").read_text(encoding="utf-8")
        for text in (
            "business_flow_proposal",
            "阶段",
            "节点",
            "依赖",
            "downstream_step_inputs",
            "design_rationale",
            "不得只重复需求摘要",
            "不得生成 `.lgwf/business_flow.json`",
        ):
            self.assertIn(text, prompt)

    def test_confirm_business_flow_template_covers_three_decisions(self) -> None:
        prompt = (PACKAGE_ROOT / "04_confirm_business_flow" / "confirm_business_flow.md").read_text(encoding="utf-8")
        resource_doc = (PACKAGE_ROOT / "04_confirm_business_flow" / "resources" / "README.md").read_text(encoding="utf-8")
        for text in (
            "\"decision\": \"approve\"",
            "\"decision\": \"revise\"",
            "\"decision\": \"reject\"",
            "business_flow_approval",
            "changes",
            "reason",
            "当前 run 不生成 `.lgwf/business_flow.json`",
        ):
            self.assertIn(text, prompt + "\n" + resource_doc)

    def test_scaffold_package_rule_limits_scope_and_uses_relative_paths(self) -> None:
        script = (PACKAGE_ROOT / "05_scaffold_package" / "scripts" / "scaffold_package.py").read_text(encoding="utf-8")
        for text in (
            "scaffold_package",
            "target_package_root",
            "workflow.lgwf",
            "SKILL.md",
            "README.md",
            "docs/steps",
            "只使用相对路径",
            "禁止绝对路径",
            "禁止 `..`",
            "不向目标 package 根目录写入 `.lgwf`",
        ):
            self.assertIn(text, script)

    def test_scaffold_package_docs_define_result_contract_and_boundaries(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "05_scaffold_package" / "resources" / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "05_scaffold_package" / "resources" / "scaffold_result_contract.md").read_text(encoding="utf-8"),
            )
        )
        for text in (
            "scaffold_result",
            "create_dirs",
            "create_files",
            "derived_from_business_flow",
            "target_package_root",
            "只使用相对路径",
            "不向目标 package 根目录写入 `.lgwf`",
            "ws/.lgwf",
            "当前 run 不生成 `.lgwf/business_flow.json`",
        ):
            self.assertIn(text, combined)

    def test_business_flow_boundary_docs_do_not_require_confirmed_json(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "03_propose_business_flow_react" / "agents" / "act.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "04_confirm_business_flow" / "confirm_business_flow.md").read_text(encoding="utf-8"),
            )
        )
        self.assertIn("业务流转", combined)
        self.assertIn("proposal", combined)
        self.assertIn("approval", combined)
        self.assertIn("`.lgwf/business_flow.json`", combined)
        self.assertNotIn("当前 run 必须生成 `.lgwf/business_flow.json`", combined)

    def test_scaffold_validation_docs_cover_paths_and_state_boundary(self) -> None:
        combined = "\n".join(
            (
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "tests" / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "05_scaffold_package" / "scripts" / "scaffold_package.py").read_text(encoding="utf-8"),
            )
        )
        for text in (
            "相对路径",
            "work dir",
            "ws/.lgwf",
            "不向目标 package 根目录写入 `.lgwf`",
            "脚手架",
            "验证",
        ):
            self.assertIn(text, combined)

    def test_design_steps_prompt_and_spec_define_consumable_doc_contract(self) -> None:
        prompt = (PACKAGE_ROOT / "06_design_steps_react" / "agents" / "act.md").read_text(encoding="utf-8")
        spec = (PACKAGE_ROOT / "06_design_steps_react" / "agents" / "spec.md").read_text(encoding="utf-8")
        combined = prompt + "\n" + spec
        for text in (
            "docs/steps/*.md",
            "step_slug",
            "goal",
            "inputs",
            "outputs",
            "dependencies",
            "implementation_suggestions",
            "acceptance_notes",
            "out_of_scope",
            "`.lgwf/step_designs.json`",
            "UTF-8 Markdown",
        ):
            self.assertIn(text, combined)

    def test_step_docs_template_fields_align_with_implementation_contract(self) -> None:
        readme = (PACKAGE_ROOT / "docs" / "steps" / "README.md").read_text(encoding="utf-8")
        template = (PACKAGE_ROOT / "docs" / "steps" / "step-design-template.md").read_text(encoding="utf-8")
        implement = (PACKAGE_ROOT / "08_implement_steps_react" / "agents" / "act.md").read_text(encoding="utf-8")
        combined = readme + "\n" + template + "\n" + implement
        for text in (
            "docs/steps/<step-slug>.md",
            "step_slug",
            "step_name",
            "goal",
            "inputs",
            "outputs",
            "dependencies",
            "implementation_suggestions",
            "acceptance_notes",
            "out_of_scope",
            "workflow 初稿",
            "直接消费",
        ):
            self.assertIn(text, combined)

    def test_confirm_step_designs_template_covers_three_decisions_and_boundary(self) -> None:
        prompt = (PACKAGE_ROOT / "07_confirm_step_designs" / "confirm_step_designs.md").read_text(encoding="utf-8")
        resource_doc = (PACKAGE_ROOT / "07_confirm_step_designs" / "resources" / "README.md").read_text(encoding="utf-8")
        fixture = (PACKAGE_ROOT / "07_confirm_step_designs" / "resources" / "step_design_approval_example.json").read_text(
            encoding="utf-8"
        )
        combined = prompt + "\n" + resource_doc + "\n" + fixture
        for text in (
            "\"decision\": \"approve\"",
            "\"decision\": \"revise\"",
            "\"decision\": \"reject\"",
            "approved_step_slugs",
            "step_design_confirmation_record",
            "当前 run 不生成 `.lgwf/step_designs.json`",
        ):
            self.assertIn(text, combined)

    def test_implement_steps_prompt_and_spec_limit_scope_to_workflow_draft(self) -> None:
        prompt = (PACKAGE_ROOT / "08_implement_steps_react" / "agents" / "act.md").read_text(encoding="utf-8")
        spec = (PACKAGE_ROOT / "08_implement_steps_react" / "agents" / "spec.md").read_text(encoding="utf-8")
        readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
        combined = prompt + "\n" + spec + "\n" + readme
        for text in (
            "workflow 初稿",
            "docs/steps/*.md",
            "只按已确认设计",
            "不负责 `lgwf-wf-prompt-fix` 集成",
            "不负责 `lgwf-wf-agent` 集成",
            "自动修复",
            "端到端运行保证",
            "不把 `.lgwf/step_designs.json` 当成 produced artifact 或通过前提",
        ):
            self.assertIn(text, combined)


class WorkflowCreateScaffoldContractTest(WorkflowCreateFoundationContractTest):
    """兼容旧测试入口名，当前内容只验证 foundation 契约。"""


if __name__ == "__main__":
    unittest.main()
