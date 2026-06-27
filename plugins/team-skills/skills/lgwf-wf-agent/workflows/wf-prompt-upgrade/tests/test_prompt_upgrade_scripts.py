from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    path = ROOT / "wf" / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PromptUpgradeScriptsTest(unittest.TestCase):
    def test_prompt_upgrade_workflow_uses_owned_namespace_and_confirmation(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("WORKFLOW lgwf_wf_prompt_upgrade;", source)
        self.assertIn("ENTRY init_prompt_upgrade_target;", source)
        self.assertIn("APPROVAL init_prompt_upgrade_target", source)
        self.assertIn("READ state.prompt_upgrade_target", source)
        self.assertIn("WRITE state.lgwf_wf_prompt_upgrade.prompt_upgrade_target", source)
        self.assertIn('PERSIST ".lgwf/prompt_upgrade_target.json"', source)
        self.assertIn("PY check_lgwf_client_assist", source)
        self.assertIn("REACT design_prompt_upgrade MAX 3", source)
        self.assertIn("APPROVAL confirm_prompt_upgrade", source)
        self.assertIn("REACT apply_prompt_upgrade MAX 3", source)
        self.assertNotIn("APPROVAL confirm_prompt_upgrade_summary", source)
        self.assertIn(".lgwf/prompt_upgrade/inventory.json", source)
        self.assertIn(".lgwf/prompt_upgrade/proposal.json", source)
        self.assertIn(".lgwf/prompt_upgrade/decision.json", source)
        observe_prompt = (ROOT / "wf" / "04_apply_upgrade" / "agents" / "observe.md").read_text(encoding="utf-8")
        self.assertIn(".lgwf/prompt_upgrade/apply_review.json", observe_prompt)
        self.assertNotIn(".lgwf/prompt_acceptance", source)
        self.assertIn('WHEN "apply" THEN apply_prompt_upgrade', source)
        self.assertIn('WHEN "summarize" THEN summarize_prompt_upgrade', source)
        self.assertIn("FLOW apply_prompt_upgrade\n  THEN summarize_prompt_upgrade;", source)
        self.assertNotIn("THEN confirm_prompt_upgrade_summary", source)

    def test_environment_check_detects_missing_and_present_skill(self) -> None:
        check_mod = load_module(
            "00_check_environment/scripts/check_lgwf_client_assist.py",
            "upgrade_env_check",
        )
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            found = Path(temp) / "skill"
            found.mkdir()
            (found / "AGENTS.md").write_text("# lgwf-client-assist\n", encoding="utf-8")
            failed = check_mod.find_lgwf_client_assist([missing])
            self.assertFalse(failed["passed"])
            self.assertIn("lgwf-client-assist", failed["reason"])
            passed = check_mod.find_lgwf_client_assist([missing, found])
            self.assertTrue(passed["passed"])
            self.assertEqual(Path(passed["skill_md"]), found / "AGENTS.md")

    def test_environment_check_rejects_legacy_skill_marker_only(self) -> None:
        check_mod = load_module(
            "00_check_environment/scripts/check_lgwf_client_assist.py",
            "upgrade_env_check_legacy_marker",
        )
        with tempfile.TemporaryDirectory() as temp:
            legacy = Path(temp) / "legacy"
            legacy.mkdir()
            (legacy / "SKILL.md").write_text("# lgwf-client-assist\n", encoding="utf-8")
            result = check_mod.find_lgwf_client_assist([legacy])
            self.assertFalse(result["passed"])

    def test_prompt_inventory_discovers_prompt_references_in_nested_workflows(self) -> None:
        inventory_mod = load_module(
            "01_inventory/scripts/build_prompt_inventory.py",
            "upgrade_inventory",
        )
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "target"
            nested = package / "child"
            prompt = nested / "agents" / "prompt.md"
            approval = package / "approve.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("# Role\nDo work.\n", encoding="utf-8")
            approval.write_text("确认。\n", encoding="utf-8")
            (package / "workflow.lgwf").write_text(
                'WORKFLOW root;\nAPPROVAL confirm\n  PROMPT_REF "approve.md";\n',
                encoding="utf-8",
            )
            (nested / "workflow.lgwf").write_text(
                'WORKFLOW child;\nREACT demo MAX 3\n'
                '  REASON CODEX\n'
                '    PROMPT "agents/prompt.md"\n',
                encoding="utf-8",
            )
            inventory = inventory_mod.build_prompt_inventory(package / "workflow.lgwf")
        paths = {item["prompt_path"] for item in inventory["prompts"]}
        self.assertEqual(paths, {"approve.md", "child/agents/prompt.md"})
        self.assertTrue(all(item["artifact_root"] == ".lgwf/prompt_upgrade" for item in inventory["prompts"]))

    def test_design_decide_requires_review_pass_and_non_empty_upgrades(self) -> None:
        decide_mod = load_module(
            "02_design_upgrade/scripts/decide_prompt_upgrade_design.py",
            "upgrade_design_decide",
        )
        self.assertTrue(
            decide_mod.design_ready(
                {"prompt_upgrades": [{"id": "upgrade_1"}]},
                {"passed": True, "ready_for_confirmation": True, "blocking_issues": []},
            )
        )
        self.assertFalse(
            decide_mod.design_ready(
                {"prompt_upgrades": []},
                {"passed": True, "ready_for_confirmation": True, "blocking_issues": []},
            )
        )

    def test_upgrade_decision_supports_all_partial_and_reject(self) -> None:
        decision_mod = load_module(
            "03_confirm_upgrade/scripts/validate_prompt_upgrade_decision.py",
            "upgrade_decision",
        )
        proposal = {"prompt_upgrades": [{"id": "u1"}, {"id": "u2"}]}
        self.assertEqual(
            decision_mod.normalize_decision({"approve": True}, proposal)["approved_upgrade_ids"],
            ["u1", "u2"],
        )
        self.assertEqual(
            decision_mod.normalize_decision({"approve": True, "approved_upgrade_ids": ["u2", "missing"]}, proposal)[
                "approved_upgrade_ids"
            ],
            ["u2"],
        )
        rejected = decision_mod.normalize_decision({"reject": True, "comment": "later"}, proposal)
        self.assertTrue(rejected["reject"])
        self.assertFalse(rejected["approve"])

    def test_route_after_decision(self) -> None:
        route_mod = load_module(
            "03_confirm_upgrade/scripts/route_after_prompt_upgrade_decision.py",
            "upgrade_route",
        )
        self.assertEqual(route_mod.choose_route({"approve": True, "approved_upgrade_ids": ["u1"]}), "apply")
        self.assertEqual(route_mod.choose_route({"reject": True, "approved_upgrade_ids": []}), "summarize")

    def test_apply_decide_exits_when_no_remaining_upgrades(self) -> None:
        decide_mod = load_module(
            "04_apply_upgrade/scripts/decide_prompt_upgrade_apply.py",
            "upgrade_apply_decide",
        )
        self.assertEqual(decide_mod.choose_next({"passed": True, "remaining_upgrade_ids": []}), "exit")
        self.assertEqual(decide_mod.choose_next({"passed": False, "remaining_upgrade_ids": ["u1"]}), "continue")
        self.assertEqual(
            decide_mod.choose_next(
                {
                    "passed": False,
                    "remaining_upgrade_ids": [],
                    "issues": [
                        "Content checks passed, but the target package is untracked in git, so out-of-plan file changes cannot be proven absent with VCS evidence."
                    ],
                    "unexpected_changes": [
                        "git status shows the target package as untracked, so unexpected changed files cannot be enumerated from VCS."
                    ],
                    "step_results": [{"passed": True}],
                    "missing_changes": [],
                }
            ),
            "exit",
        )
        self.assertEqual(
            decide_mod.choose_next(
                {
                    "passed": False,
                    "remaining_upgrade_ids": [],
                    "issues": ["approved prompt upgrade is missing required output contract"],
                    "step_results": [{"passed": True}],
                    "missing_changes": [],
                }
            ),
            "continue",
        )

    def test_summary_statuses(self) -> None:
        summary_mod = load_module(
            "05_summary/scripts/summarize_prompt_upgrade.py",
            "upgrade_summary",
        )
        base = {
            "inventory": {"prompts": [{"prompt_path": "agents/prompt.md"}]},
            "proposal": {"prompt_upgrades": [{"id": "u1"}], "files_to_modify": ["agents/prompt.md"]},
            "history": [],
        }
        upgraded = summary_mod.build_summary(
            **base,
            decision={"approve": True, "approved_upgrade_ids": ["u1"]},
            review={"passed": True, "remaining_upgrade_ids": []},
        )
        self.assertEqual(upgraded["status"], "upgraded")
        rejected = summary_mod.build_summary(
            **base,
            decision={"reject": True, "approved_upgrade_ids": []},
            review={},
        )
        self.assertEqual(rejected["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
