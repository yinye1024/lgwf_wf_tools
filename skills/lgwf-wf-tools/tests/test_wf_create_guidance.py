from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WfCreateGuidanceTest(unittest.TestCase):
    def test_router_requires_guidance_before_wf_create_fast_without_raw_intent(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        workflow_inputs = (ROOT / "docs" / "workflow-inputs.md").read_text(encoding="utf-8")
        wf_create_agents = (ROOT / "workflows" / "wf-create-fast" / "AGENTS.md").read_text(encoding="utf-8")

        for text in (agents, workflow_inputs, wf_create_agents):
            self.assertIn("raw_intent", text)
            self.assertIn("初步计划", text)
            self.assertIn("不直接启动", text)
            self.assertIn("target_file", text)

        self.assertIn("目标不明确", agents)
        self.assertIn("wf-create-fast 启动前输入模板", workflow_inputs)
        self.assertIn("计划文档路径", workflow_inputs)
        self.assertIn("启动前整理", wf_create_agents)

    def test_wf_create_fast_replaces_wf_create_in_registry(self) -> None:
        registry = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
        ids = {item["id"] for item in registry["workflows"]}
        self.assertIn("wf-create-fast", ids)
        self.assertNotIn("wf-create", ids)


if __name__ == "__main__":
    unittest.main()
