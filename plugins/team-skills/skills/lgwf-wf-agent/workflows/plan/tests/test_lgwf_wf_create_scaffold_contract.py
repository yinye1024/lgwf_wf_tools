from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[7]
PACKAGE_ROOT = ROOT / "plugins" / "team-skills" / "skills" / "lgwf-wf-agent" / "workflows" / "wf-create"
WF_ROOT = PACKAGE_ROOT / "wf"


class WorkflowCreateInternalPackageContractTest(unittest.TestCase):
    def test_package_is_facade_internal_workflow(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "README.md").is_file())
        self.assertTrue((PACKAGE_ROOT / "AGENTS.md").is_file())
        self.assertTrue((WF_ROOT / "workflow.lgwf").is_file())
        self.assertFalse((PACKAGE_ROOT / "SKILL.md").exists())
        self.assertFalse((PACKAGE_ROOT / "workflow.lgwf").exists())

    def test_package_core_dirs_exist(self) -> None:
        for relative in ("wf", "ws", "tests", "wf/docs/steps"):
            self.assertTrue((PACKAGE_ROOT / relative).is_dir(), relative)

    def test_workflow_stage_order_and_relative_paths(self) -> None:
        text = (WF_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("..", text)
        self.assertIsNone(re.search(r"[A-Za-z]:[\\/]", text))
        self.assertIsNone(re.search(r"\b(?:https?|file)://", text))

        expected_fragments = (
            'WORKFLOW "02_confirm_requirements/workflow.lgwf"',
            'WORKFLOW "04_confirm_business_flow/workflow.lgwf"',
            'WORKFLOW "07_confirm_step_designs/workflow.lgwf"',
            'WORKFLOW "09_summarize_create_result/workflow.lgwf"',
        )
        for fragment in expected_fragments:
            self.assertIn(fragment, text)

        ordered_names = (
            "define_requirements",
            "design_structure",
            "implement_draft",
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
                (PACKAGE_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8"),
                (PACKAGE_ROOT / "tests" / "README.md").read_text(encoding="utf-8"),
            )
        )
        for text in (
            "内部 workflow",
            "registry",
            "workflow 初稿",
            "ws/.lgwf",
            "不负责把生成出的目标 workflow 自动接入 facade 路由",
            "UTF-8",
            "中文",
        ):
            self.assertIn(text, combined)

    def test_package_has_no_runtime_pollution(self) -> None:
        forbidden = {".tmp", "__pycache__", ".lgwf"}
        for path in PACKAGE_ROOT.rglob("*"):
            if "ws" in path.relative_to(PACKAGE_ROOT).parts:
                continue
            self.assertNotIn(path.name, forbidden, path)


class WorkflowCreateScaffoldContractTest(WorkflowCreateInternalPackageContractTest):
    """兼容旧测试入口名，当前内容验证 facade 内部 `wf-create` 契约。"""


if __name__ == "__main__":
    unittest.main()
