from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "$extract"))

from lgwf_dsl.lowerer import WorkflowLowerer
from lgwf_dsl.parser import Parser
from lgwf_dsl.validator import WorkflowValidator
from lgwf.capabilities.subgraph.agent_loop.capability import SubgraphAgentLoopCapability


class AgentLoopWorkflowSlotTest(unittest.TestCase):
    def test_agent_loop_slot_can_reference_workflow_with_result_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = root / "verify_review.lgwf"
            child.write_text(
                """
WORKFLOW verify_review;
ENTRY write_verification;

PY write_verification
  SCRIPT "scripts/write_verification.py"
  RESULT state.demo.verification
  UPDATES_STATE;
""".strip()
                + "\n",
                encoding="utf-8",
            )
            parent = root / "workflow.lgwf"
            parent.write_text(
                """
WORKFLOW parent;
ENTRY repair_loop;

AGENT_LOOP repair_loop MAX_ITERATIONS 2 ARTIFACTS ".lgwf/loops/repair" {
  GOAL "repair"
  OBSERVE PY observe
    SCRIPT "scripts/observe.py"
    RESULT state.demo.observe
    UPDATES_STATE;
  DIAGNOSE CODEX diagnose
    PROMPT "agents/diagnose.md"
    RESULT state.demo.diagnose;
  PLAN CODEX plan
    PROMPT "agents/plan.md"
    RESULT state.demo.plan;
  ACT CODEX act
    PROMPT "agents/act.md"
    RESULT state.demo.act;
  VERIFY WORKFLOW verify_review
    WORKFLOW "verify_review.lgwf"
    RESULT state.demo.verification;
  DECIDE PY decide
    SCRIPT "scripts/decide.py"
    RESULT state.demo.decision
    UPDATES_STATE;
};
""".strip()
                + "\n",
                encoding="utf-8",
            )

            ast = Parser.from_text(parent.read_text(encoding="utf-8"), source_name=str(parent)).parse_workflow()
            WorkflowValidator().validate(ast)
            workflow = WorkflowLowerer().lower(ast)

        loop_node = workflow["nodes"][0]
        self.assertEqual(loop_node["capability"], "subgraph.agent_loop")
        verify_slot = loop_node["config"]["verify"]
        self.assertEqual(verify_slot["capability"], "subgraph.workflow")
        self.assertEqual(verify_slot["config"]["result_path"], "demo.verification")
        self.assertEqual(verify_slot["config"]["workflow"]["entry_point"], "write_verification")

    def test_agent_loop_workflow_slot_requires_result_path(self) -> None:
        source = """
WORKFLOW parent;
ENTRY repair_loop;

AGENT_LOOP repair_loop MAX_ITERATIONS 2 ARTIFACTS ".lgwf/loops/repair" {
  GOAL "repair"
  OBSERVE PY observe SCRIPT "scripts/observe.py" RESULT state.demo.observe UPDATES_STATE;
  DIAGNOSE CODEX diagnose PROMPT "agents/diagnose.md" RESULT state.demo.diagnose;
  PLAN CODEX plan PROMPT "agents/plan.md" RESULT state.demo.plan;
  ACT CODEX act PROMPT "agents/act.md" RESULT state.demo.act;
  VERIFY WORKFLOW verify_review WORKFLOW "verify_review.lgwf";
  DECIDE PY decide SCRIPT "scripts/decide.py" RESULT state.demo.decision UPDATES_STATE;
};
""".strip()
        with self.assertRaisesRegex(Exception, "requires RESULT"):
            Parser.from_text(source).parse_workflow()

    def test_agent_loop_runtime_accepts_workflow_slot(self) -> None:
        assign_node = {
            "capability": "flow.assign",
            "config": {"assignments": {"demo.slot": {"ok": True}}},
        }
        workflow_slot = {
            "capability": "subgraph.workflow",
            "config": {
                "workflow": {
                    "nodes": [
                        {
                            "id": "verify",
                            "capability": "flow.assign",
                            "config": {"assignments": {"demo.verification": {"passed": True}}},
                        }
                    ],
                    "edges": [],
                    "routes": [],
                    "entry_point": "verify",
                },
                "result_path": "demo.verification",
            },
        }
        config = {
            "max_iterations": 1,
            "artifacts_path": ".lgwf/loops/repair",
            "goal": "repair",
            "observe": assign_node,
            "diagnose": assign_node,
            "plan": assign_node,
            "act": assign_node,
            "verify": workflow_slot,
            "decide": assign_node,
        }

        node = SubgraphAgentLoopCapability().create_node("repair_loop", config)

        self.assertTrue(callable(node))


if __name__ == "__main__":
    unittest.main()
