from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class StructuredContractsTest(unittest.TestCase):
    def test_init_plan_preserves_structured_fields(self) -> None:
        manager = load_module("04_execute_react_loop/00_prepare/scripts/manage_react_task.py", "manager")
        with tempfile.TemporaryDirectory() as temp:
            plan = {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "title": "Title",
                        "scope_detail": {"files": ["a.py"]},
                        "implementation_steps": [{"step": "change"}],
                        "acceptance_seed": ["seed"],
                        "required_checks_hint": ["python -m unittest"],
                    }
                ]
            }
            stored = manager.init_plan(Path(temp), plan)
            task = stored["tasks"][0]
            self.assertEqual(task["scope_detail"], {"files": ["a.py"]})
            self.assertEqual(task["implementation_steps"], [{"step": "change"}])
            self.assertEqual(task["status"], "planned")

    def test_set_acceptance_requires_plan_validation_map_coverage(self) -> None:
        manager = load_module("04_execute_react_loop/00_prepare/scripts/manage_react_task.py", "manager2")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager.init_plan(root, {"tasks": [{"task_id": "task-1", "implementation_steps": ["a", "b"]}]})
            acceptance = {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "criteria": ["done"],
                        "required_checks": ["test"],
                        "review_focus": ["scope"],
                        "out_of_scope": ["unrelated files"],
                        "plan_validation_map": [
                            {"plan_step_index": 0, "plan_step": "a", "expected_evidence": "x", "validation": "check"},
                            {"plan_step_index": 1, "plan_step": "b", "expected_evidence": "y", "validation": "check"},
                        ],
                    }
                ]
            }
            manager.set_acceptance(root, acceptance)
            stored = json.loads((root / ".lgwf" / "react_acceptance_plan.json").read_text(encoding="utf-8"))
            indexes = [item["plan_step_index"] for item in stored["tasks"][0]["plan_validation_map"]]
            self.assertEqual(indexes, [0, 1])

    def test_set_acceptance_rejects_missing_plan_validation_map_coverage(self) -> None:
        manager = load_module("04_execute_react_loop/00_prepare/scripts/manage_react_task.py", "manager3")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager.init_plan(root, {"tasks": [{"task_id": "task-1", "implementation_steps": ["a", "b"]}]})
            acceptance = {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "criteria": ["done"],
                        "required_checks": ["test"],
                        "review_focus": ["scope"],
                        "out_of_scope": ["unrelated files"],
                        "plan_validation_map": [
                            {"plan_step_index": 0, "plan_step": "a", "expected_evidence": "x", "validation": "check"}
                        ],
                    }
                ]
            }
            with self.assertRaisesRegex(ValueError, "cover implementation_steps"):
                manager.set_acceptance(root, acceptance)

    def test_record_review_rejects_pass_without_evidence_details(self) -> None:
        record = load_module("04_execute_react_loop/02_record/scripts/record_react_task_review.py", "record")
        with self.assertRaises(SystemExit):
            record.validate_result({"verdict": "pass", "pass": True, "accepted": True, "required_follow_up": []})

    def test_record_review_accepts_structured_pass_details(self) -> None:
        record = load_module("04_execute_react_loop/02_record/scripts/record_react_task_review.py", "record2")
        record.validate_result(
            {
                "verdict": "pass",
                "pass": True,
                "accepted": True,
                "evidence": ["tests passed"],
                "criteria_results": [{"criteria": "done", "passed": True}],
                "required_check_results": [{"check": "unit", "passed": True}],
                "plan_validation_results": [{"plan_step_index": 0, "passed": True}],
                "scope_compliance": {"within_scope": True, "issues": []},
                "required_follow_up": [],
            }
        )

    def test_decide_scripts_emit_top_level_next(self) -> None:
        for relative, observe_name, proposal_name in (
            ("01_generate_plan/02_generate_plan_proposal/scripts/decide.py", "react_task_plan_observe.json", "react_task_plan_proposal.json"),
            ("02_generate_acceptance/00_generate_acceptance_proposal/scripts/decide.py", "react_acceptance_observe.json", "react_acceptance_proposal.json"),
            ("04_execute_react_loop/01_implement_task/scripts/decide.py", "react_task_result.json", None),
        ):
            self.assertTrue((ROOT / relative).exists())
            self.assertIn("next", (ROOT / relative).read_text(encoding="utf-8"))

    def test_confirmation_template_mentions_structured_fields(self) -> None:
        template = (ROOT / "03_confirm_plan_and_acceptance/00_user_decision_template/plan_acceptance_decision_template.md").read_text(encoding="utf-8")
        for text in ("scope_detail", "implementation_steps", "criteria_details", "required_checks_details", "traceability", "plan_validation_map"):
            self.assertIn(text, template)


if __name__ == "__main__":
    unittest.main()
