from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LgwfGuideTest(unittest.TestCase):
    def test_registry_declares_stateless_tool_workflow(self) -> None:
        registry = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
        workflows = {item["id"]: item for item in registry["workflows"]}
        guide = workflows["lgwf-guide"]

        self.assertEqual("tool-workflow", guide["kind"])
        self.assertEqual("docs/lgwf-guide.md", guide["entry"])
        self.assertEqual("workflows/lgwf-guide/AGENTS.md", guide["agents_md"])
        self.assertNotIn("workflow_lgwf", guide)
        self.assertNotIn("work_dir", guide)

    def test_contract_forbids_runtime_state_and_target_writes(self) -> None:
        contract = json.loads(
            (ROOT / "workflows" / "lgwf-guide" / "entry_contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual("tool_args", contract["input_mode"])
        self.assertEqual("not_applicable", contract["auto_human_policy"])
        self.assertEqual("none", contract["state_boundary"]["runtime_state"])
        self.assertEqual("none", contract["state_boundary"]["target_writes"])
        self.assertEqual("none", contract["target_scope"]["write_scope"])

    def test_guide_is_conversational_and_has_no_lgwf_source(self) -> None:
        module_root = ROOT / "workflows" / "lgwf-guide"
        agents = (module_root / "AGENTS.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "lgwf-guide.md").read_text(encoding="utf-8")

        self.assertFalse(any(module_root.rglob("workflow.lgwf")))
        self.assertIn("普通对话", agents)
        self.assertIn("不得调用 `scripts/run_skill_workflow.py`", agents)
        self.assertIn("默认开场", guide)
        self.assertIn("三个优先核心问题", agents)
        self.assertIn("下面 7 个问题", guide)
        self.assertIn("优先核心三问", guide)
        self.assertIn("进阶四问", guide)
        self.assertIn("我为什么要用 LGWF，而不是继续使用现在的 prompt 工作流？", guide)
        self.assertIn("什么情况下又没有必要迁移？", guide)
        self.assertIn("请用仓库中一个最小 workflow", guide)
        self.assertIn("`workflow.lgwf` 的核心语法有哪些？", guide)
        self.assertIn("`work_dir`、run、节点结果和产物之间是什么关系？", guide)
        self.assertIn("`approval`、`review`、`human_choice`、`waiting_human`", guide)
        self.assertIn("workflow 失败或中断后", guide)
        self.assertIn("LGWF 引擎、`lgwf-client-assist`、`lgwf-wf-tools`", guide)
        self.assertIn("一次性提问模板", guide)
        self.assertIn("LGWF 增加了哪些能力、引入了哪些成本、什么情况下不值得迁移", guide)
        self.assertIn("优先问第 **1、2、3** 题", guide)
        self.assertIn("补充提问路径", guide)
        self.assertIn("本模块自身不启动任何 workflow", guide)

    def test_commands_and_router_expose_guide(self) -> None:
        commands = json.loads((ROOT / "commands.json").read_text(encoding="utf-8"))["commands"]
        command_names = {item["command"] for item in commands}
        router = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        maintenance = (ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8")

        for command in (
            "/lgwf-wf-tools guide",
            "/lgwf-wf-tools learn",
            "/lgwf-wf-tools 入门",
        ):
            self.assertIn(command, command_names)
            self.assertIn(command, skill)
        self.assertIn("选择 `lgwf-guide`", router)
        self.assertIn("doctor 通过且用户没有给出具体任务", maintenance)
        self.assertIn("路由到 `lgwf-guide`", maintenance)


if __name__ == "__main__":
    unittest.main()
