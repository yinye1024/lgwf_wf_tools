from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
LGWF = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


class ChoiceDslTests(unittest.TestCase):
    def test_choice_compiles_to_human_choice_with_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompt = root / "choice.md"
            prompt.write_text("请选择下一步。", encoding="utf-8")
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW choice_demo;
ENTRY choose_next;

CHOICE choose_next
  PROMPT_REF "choice.md"
  OPTIONS ["run", "skip", "auto", "stop"]
  READ state.choice_context
  WRITE state.choice_decision
  RESULT state.choice_result
  PERSIST ".lgwf/choice.json"
  POLL 1;

ROUTE choose_next
  WHEN "run" THEN finish
  WHEN "skip" THEN finish
  WHEN "auto" THEN finish
  WHEN "stop" THEN finish;

PY finish
  SCRIPT "finish.py";
""".lstrip(),
                encoding="utf-8",
            )
            (root / "finish.py").write_text("print('{}')", encoding="utf-8")
            output = root / "workflow.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(LGWF),
                    "compile",
                    str(workflow),
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            compiled = json.loads(output.read_text(encoding="utf-8"))
            node = next(item for item in compiled["nodes"] if item["id"] == "choose_next")
            self.assertEqual("flow.human_choice", node["capability"])
            self.assertEqual(["run", "skip", "auto", "stop"], node["config"]["options"])
            self.assertEqual("choice_decision", node["config"]["choice_value_path"])

    def test_human_nodes_support_inline_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("review.md", "choice.md"):
                (root / name).write_text("请选择下一步。", encoding="utf-8")
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW inline_routes_demo;
ENTRY approve_gate;

APPROVAL approve_gate
  PROMPT "是否继续？"
  READ state.approval_context
  WRITE state.approval_value
  ROUTES {"approve": "review_gate", "reject": "finish"};

REVIEW review_gate
  PROMPT_REF "review.md"
  CONTEXT state.review_context
  OPTIONS ["approve", "revise", "reject"]
  ROUTES {"approve": "choice_gate", "revise": "finish", "reject": "finish"};

CHOICE choice_gate
  PROMPT_REF "choice.md"
  OPTIONS ["run", "skip", "auto", "stop"]
  READ state.choice_context
  WRITE state.choice_decision
  ROUTES {"run": "finish", "skip": "finish", "auto": "finish", "stop": "finish"};

PY finish
  SCRIPT "finish.py";
""".lstrip(),
                encoding="utf-8",
            )
            (root / "finish.py").write_text("print('{}')", encoding="utf-8")
            output = root / "workflow.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(LGWF),
                    "compile",
                    str(workflow),
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            compiled = json.loads(output.read_text(encoding="utf-8"))
            routes = {item["from"]: item["branches"] for item in compiled["routes"]}
            self.assertEqual({"approve": "review_gate", "reject": "finish"}, routes["approve_gate"])
            self.assertEqual(
                {"approve": "choice_gate", "revise": "finish", "reject": "finish"},
                routes["review_gate"],
            )
            self.assertEqual(
                {"run": "finish", "skip": "finish", "auto": "finish", "stop": "finish"},
                routes["choice_gate"],
            )
            approval = next(item for item in compiled["nodes"] if item["id"] == "approve_gate")
            self.assertTrue(approval["config"]["route_on_decision"])

    def test_choice_routes_can_derive_options_without_state_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "choice.md").write_text("请选择下一步。", encoding="utf-8")
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW compact_choice_demo;
ENTRY choose_next;

CHOICE choose_next
  PROMPT_REF "choice.md"
  ROUTES {"run": "finish", "skip": "finish", "auto": "finish", "stop": "finish"};

PY finish
  SCRIPT "finish.py";
""".lstrip(),
                encoding="utf-8",
            )
            (root / "finish.py").write_text("print('{}')", encoding="utf-8")
            output = root / "workflow.json"

            completed = subprocess.run(
                [sys.executable, str(LGWF), "compile", str(workflow), "--output", str(output)],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            compiled = json.loads(output.read_text(encoding="utf-8"))
            node = next(item for item in compiled["nodes"] if item["id"] == "choose_next")
            self.assertEqual(["run", "skip", "auto", "stop"], node["config"]["options"])
            self.assertNotIn("context_path", node["config"])
            self.assertNotIn("choice_value_path", node["config"])
            self.assertEqual(
                {"run": "finish", "skip": "finish", "auto": "finish", "stop": "finish"},
                compiled["routes"][0]["branches"],
            )

    def test_route_read_and_human_routes_can_target_named_flows(self) -> None:
        workflow = """
WORKFLOW route_read_demo;
ENTRY auto_route;

ROUTE auto_route
  READ state.flags.auto
  WHEN true THEN run_flow
  WHEN false THEN choose_next;

CHOICE choose_next
  PROMPT "请选择下一步。"
  ROUTES {"run": "run_flow", "skip": "skip_flow"};

PY build
  SCRIPT "finish.py";

PY finish
  SCRIPT "finish.py";

PY skip
  SCRIPT "finish.py";

FLOW run_flow
  START build
  THEN finish;

FLOW skip_flow
  START skip;
""".lstrip()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow_path = root / "workflow.lgwf"
            workflow_path.write_text(workflow, encoding="utf-8")
            (root / "finish.py").write_text("print('{}')", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(LGWF),
                    "compile",
                    str(workflow_path),
                    "--output",
                    str(root / "workflow.json"),
                ],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            compiled = json.loads((root / "workflow.json").read_text(encoding="utf-8"))
            route_node = next(item for item in compiled["nodes"] if item["id"] == "auto_route")
            self.assertEqual("flow.switch", route_node["capability"])
            self.assertEqual("flags.auto", route_node["config"]["path"])
            self.assertIn(["build", "finish"], compiled["edges"])
            routes = {item["from"]: item["branches"] for item in compiled["routes"]}
            self.assertEqual({"true": "build", "false": "choose_next"}, routes["auto_route"])
            self.assertEqual({"run": "build", "skip": "skip"}, routes["choose_next"])

    def test_choice_rejects_options_routes_mismatch(self) -> None:
        workflow = """
WORKFLOW mismatch_demo;
ENTRY choose_next;

CHOICE choose_next
  PROMPT "请选择下一步。"
  OPTIONS ["run", "skip"]
  ROUTES {"run": "finish", "stop": "finish"};

PY finish
  SCRIPT "finish.py";
""".lstrip()

        completed = self._compile_text(workflow)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("CHOICE OPTIONS must match ROUTES keys", completed.stderr + completed.stdout)

    def test_inline_routes_conflict_with_external_route_is_invalid(self) -> None:
        workflow = """
WORKFLOW route_conflict_demo;
ENTRY choose_next;

CHOICE choose_next
  PROMPT "请选择下一步。"
  ROUTES {"run": "finish", "skip": "finish"};

ROUTE choose_next
  WHEN "run" THEN other
  WHEN "skip" THEN finish;

PY finish
  SCRIPT "finish.py";

PY other
  SCRIPT "finish.py";
""".lstrip()

        completed = self._compile_text(workflow)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("conflict with external ROUTE", completed.stderr + completed.stdout)

    def test_review_routes_are_fixed_three_keys(self) -> None:
        workflow = """
WORKFLOW review_fixed_demo;
ENTRY review_next;

REVIEW review_next
  PROMPT_REF "review.md"
  ROUTES {"approve": "finish", "revise": "finish", "skip": "finish"};

PY finish
  SCRIPT "finish.py";
""".lstrip()

        completed = self._compile_text(workflow)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("REVIEW ROUTES keys must be approve/revise/reject", completed.stderr + completed.stdout)

    def _compile_text(self, workflow_text: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = root / "workflow.lgwf"
            workflow.write_text(workflow_text, encoding="utf-8")
            (root / "finish.py").write_text("print('{}')", encoding="utf-8")
            (root / "review.md").write_text("请审核。", encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(LGWF),
                    "compile",
                    str(workflow),
                    "--output",
                    str(root / "workflow.json"),
                ],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )


if __name__ == "__main__":
    unittest.main()
