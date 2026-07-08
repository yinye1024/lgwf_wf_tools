from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    path = ROOT / "wf" / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PromptUpgradeScriptsTest(unittest.TestCase):
    def test_prompt_upgrade_root_workflow_wraps_major_phases_as_subworkflows(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("WORKFLOW lgwf_wf_prompt_upgrade;", source)
        self.assertIn("ENTRY prepare_target;", source)
        for step_id, workflow_path in (
            ("prepare_target", "01_prepare_target/workflow.lgwf"),
            ("design_upgrade", "02_design_upgrade/workflow.lgwf"),
            ("confirm_upgrade", "03_confirm_upgrade/workflow.lgwf"),
            ("apply_upgrade", "04_apply_upgrade/workflow.lgwf"),
            ("summary", "05_summary/workflow.lgwf"),
        ):
            self.assertIn(f"STEP {step_id}\n  WORKFLOW \"{workflow_path}\"", source)
            self.assertTrue((ROOT / "wf" / workflow_path).is_file())
        self.assertIn('WRITE workspace file ".lgwf/prompt_upgrade/decision.json";', source)
        self.assertIn('READ workspace file ".lgwf/prompt_upgrade/decision.json";', source)
        self.assertNotIn("APPROVAL init_prompt_upgrade_target", source)
        self.assertNotIn("REACT design_prompt_upgrade", source)
        self.assertNotIn("REACT apply_prompt_upgrade", source)

    def test_prompt_upgrade_workflow_layout_is_two_layers(self) -> None:
        workflows = sorted(path.relative_to(ROOT / "wf").as_posix() for path in (ROOT / "wf").rglob("workflow.lgwf"))
        self.assertEqual(
            workflows,
            [
                "01_prepare_target/workflow.lgwf",
                "02_design_upgrade/workflow.lgwf",
                "03_confirm_upgrade/workflow.lgwf",
                "04_apply_upgrade/workflow.lgwf",
                "05_summary/workflow.lgwf",
                "workflow.lgwf",
            ],
        )
        for workflow in workflows:
            if workflow == "workflow.lgwf":
                continue
            self.assertEqual(len(Path(workflow).parts), 2)
        apply_source = (ROOT / "wf" / "04_apply_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn('WORKFLOW "act_apply_prompt_upgrade/workflow.lgwf"', apply_source)
        self.assertNotIn("ACT WORKFLOW apply_prompt_upgrade_once", apply_source)
        self.assertIn("ACT CODEX", apply_source)
        self.assertIn('PROMPT "agents/act.md"', apply_source)

    def test_prompt_upgrade_workflow_uses_owned_namespace_and_confirmation(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        prepare_source = (ROOT / "wf" / "01_prepare_target" / "workflow.lgwf").read_text(encoding="utf-8")
        design_source = (ROOT / "wf" / "02_design_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        confirm_source = (ROOT / "wf" / "03_confirm_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        apply_source = (ROOT / "wf" / "04_apply_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("WORKFLOW lgwf_wf_prompt_upgrade;", source)
        self.assertIn("APPROVAL init_prompt_upgrade_target", prepare_source)
        self.assertIn("READ state.prompt_upgrade_target", prepare_source)
        self.assertIn("WRITE state.lgwf_wf_prompt_upgrade.prompt_upgrade_target", prepare_source)
        self.assertIn('PERSIST ".lgwf/prompt_upgrade_target.json"', prepare_source)
        self.assertIn("PY check_lgwf_client_assist", prepare_source)
        self.assertIn("REACT design_prompt_upgrade MAX 3", design_source)
        self.assertIn("APPROVAL confirm_prompt_upgrade", confirm_source)
        self.assertIn("REACT apply_prompt_upgrade MAX 3", apply_source)
        self.assertNotIn("ACT WORKFLOW apply_prompt_upgrade_once", apply_source)
        self.assertNotIn('WORKFLOW "act_apply_prompt_upgrade/workflow.lgwf"', apply_source)
        self.assertIn("ACT CODEX", apply_source)
        self.assertIn('PROMPT "agents/act.md"', apply_source)
        self.assertNotIn("APPROVAL confirm_prompt_upgrade_summary", "\n".join([source, prepare_source, design_source, confirm_source, apply_source]))
        self.assertIn(".lgwf/prompt_upgrade/inventory.json", "\n".join([prepare_source, design_source]))
        self.assertIn(".lgwf/prompt_upgrade/proposal.json", design_source)
        self.assertIn(".lgwf/prompt_upgrade/decision.json", confirm_source)
        self.assertIn("PY route_after_prompt_upgrade_decision", confirm_source)
        self.assertIn('WHEN "reject" THEN FAIL_ALL', confirm_source)
        self.assertIn("PY route_apply_upgrade_entry", apply_source)
        self.assertIn('WHEN "apply" THEN apply_prompt_upgrade', apply_source)
        self.assertIn('WHEN "skip" THEN finish_apply_upgrade_skip', apply_source)
        observe_prompt = (ROOT / "wf" / "04_apply_upgrade" / "agents" / "observe.md").read_text(encoding="utf-8")
        self.assertIn(".lgwf/prompt_upgrade/apply_review.json", observe_prompt)
        self.assertNotIn(".lgwf/prompt_acceptance", source)
        self.assertNotIn("route_after_prompt_upgrade_decision", source)
        self.assertNotIn('WHEN "apply" THEN apply_upgrade', source)
        self.assertNotIn('WHEN "summarize" THEN summary', source)
        self.assertIn("THEN confirm_upgrade\n  THEN apply_upgrade\n  THEN summary;", source)
        self.assertNotIn("THEN confirm_prompt_upgrade_summary", source)

    def test_react_shared_context_only_references_preexisting_files(self) -> None:
        design_source = (ROOT / "wf" / "02_design_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        apply_source = (ROOT / "wf" / "04_apply_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        design_context = design_source.split("CONTEXT_SET design_prompt_upgrade_shared_context {", 1)[1].split("}", 1)[0]
        apply_context = apply_source.split("CONTEXT_SET apply_prompt_upgrade_shared_context {", 1)[1].split("}", 1)[0]

        self.assertNotIn(".lgwf/prompt_upgrade/analysis.json", design_context)
        self.assertIn("CONTEXT design_prompt_upgrade_analysis_context", design_source)
        self.assertNotIn(".lgwf/prompt_upgrade/apply_plan.json", apply_context)
        self.assertIn("CONTEXT apply_prompt_upgrade_plan_context", apply_source)

    def test_environment_check_detects_missing_and_present_skill(self) -> None:
        check_mod = load_module(
            "01_prepare_target/scripts/check_lgwf_client_assist.py",
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
            "01_prepare_target/scripts/check_lgwf_client_assist.py",
            "upgrade_env_check_legacy_marker",
        )
        with tempfile.TemporaryDirectory() as temp:
            legacy = Path(temp) / "legacy"
            legacy.mkdir()
            (legacy / "SKILL.md").write_text("# lgwf-client-assist\n", encoding="utf-8")
            result = check_mod.find_lgwf_client_assist([legacy])
            self.assertFalse(result["passed"])

    def test_environment_check_finds_bundled_client_from_isolated_workflow_path(self) -> None:
        check_mod = load_module(
            "01_prepare_target/scripts/check_lgwf_client_assist.py",
            "upgrade_env_check_isolated_path",
        )
        with tempfile.TemporaryDirectory() as temp:
            facade = Path(temp) / "lgwf-wf-tools"
            bundled = facade / "vendor" / "lgwf-client-assist"
            bundled.mkdir(parents=True)
            (bundled / "AGENTS.md").write_text("# lgwf-client-assist\n", encoding="utf-8")
            isolated_script = (
                facade
                / "workflows"
                / "wf-post-fix"
                / "ws"
                / ".lgwf"
                / "isolations"
                / "run_workflow"
                / "prompt_upgrade"
                / "work_dir"
                / ".lgwf"
                / "workflow"
                / "01_prepare_target"
                / "scripts"
                / "check_lgwf_client_assist.py"
            )
            isolated_script.parent.mkdir(parents=True)
            isolated_script.write_text("# copied script placeholder\n", encoding="utf-8")
            with mock.patch.object(check_mod, "__file__", str(isolated_script)):
                self.assertEqual(check_mod.ensure_bundled_client_dir().resolve(), bundled.resolve())

    def test_environment_check_ignores_runtime_env_override_by_default(self) -> None:
        check_mod = load_module(
            "01_prepare_target/scripts/check_lgwf_client_assist.py",
            "upgrade_env_check_no_env_override",
        )
        with tempfile.TemporaryDirectory() as temp:
            fake = Path(temp) / "fake"
            fake.mkdir()
            (fake / "AGENTS.md").write_text("# external\n", encoding="utf-8")
            old = os.environ.get("LGWF_CLIENT_ASSIST")
            os.environ["LGWF_CLIENT_ASSIST"] = str(fake)
            try:
                candidates = check_mod.candidate_skill_dirs()
            finally:
                if old is None:
                    os.environ.pop("LGWF_CLIENT_ASSIST", None)
                else:
                    os.environ["LGWF_CLIENT_ASSIST"] = old
        self.assertNotIn(fake, candidates)

    def test_prompt_inventory_discovers_prompt_references_in_nested_workflows(self) -> None:
        inventory_mod = load_module(
            "01_prepare_target/scripts/build_prompt_inventory.py",
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
        self.assertTrue(
            decide_mod.design_ready(
                {"prompt_upgrades": [{"id": "upgrade_1"}]},
                {"ok": True, "output_files": [".lgwf/prompt_upgrade/proposal_review.json"]},
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
        self.assertEqual(route_mod.choose_route({"reject": True, "approved_upgrade_ids": []}), "reject")

    def test_confirm_workflow_reject_decision_uses_fail_all_without_root_route(self) -> None:
        workflow = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        confirm_workflow = (ROOT / "wf" / "03_confirm_upgrade" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("ROUTE route_after_prompt_upgrade_decision", workflow)
        self.assertIn("ROUTE route_after_prompt_upgrade_decision", confirm_workflow)
        self.assertIn('WHEN "apply" THEN finish_prompt_upgrade_confirmation', confirm_workflow)
        self.assertIn('WHEN "summarize" THEN finish_prompt_upgrade_confirmation', confirm_workflow)
        self.assertIn('WHEN "reject" THEN FAIL_ALL', confirm_workflow)

    def test_apply_upgrade_entry_skips_when_no_approved_upgrade_ids(self) -> None:
        route_mod = load_module(
            "04_apply_upgrade/scripts/route_apply_upgrade_entry.py",
            "upgrade_apply_entry_route",
        )
        self.assertEqual(route_mod.choose_route({"approve": True, "approved_upgrade_ids": ["u1"]}), "apply")
        self.assertEqual(route_mod.choose_route({"approve": True, "approved_upgrade_ids": []}), "skip")
        self.assertEqual(route_mod.choose_route({"reject": False}), "skip")

    def test_apply_upgrade_skip_review_contract(self) -> None:
        skip_mod = load_module(
            "04_apply_upgrade/scripts/finish_apply_upgrade_skip.py",
            "upgrade_apply_skip",
        )
        review = skip_mod.build_review()
        self.assertTrue(review["passed"])
        self.assertTrue(review["skipped"])
        self.assertEqual(review["remaining_upgrade_ids"], [])

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

    def test_apply_plan_validation_limits_files_to_approved_upgrade_scope(self) -> None:
        validate_mod = load_module(
            "04_apply_upgrade/scripts/validate_apply_plan.py",
            "upgrade_validate_apply_plan",
        )
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "target"
            package.mkdir()
            target = {
                "target_package_root": str(package),
                "target_dirs": [str(package)],
            }
            proposal = {
                "prompt_upgrades": [
                    {
                        "id": "u1",
                        "prompt_path": "agents/prompt.md",
                        "workflow_path": "workflow.lgwf",
                        "files_to_modify": ["agents/prompt.md"],
                    },
                    {
                        "id": "u2",
                        "prompt_path": "agents/other.md",
                        "workflow_path": "workflow.lgwf",
                        "files_to_modify": ["agents/other.md"],
                    },
                ]
            }
            decision = {"approve": True, "approved_upgrade_ids": ["u1"]}
            self.assertTrue(
                validate_mod.validate_apply_plan(
                    {"files_to_modify": ["agents/prompt.md"], "steps": [{"upgrade_id": "u1", "file": "agents/prompt.md"}]},
                    target,
                    proposal,
                    decision,
                )["passed"]
            )
            self.assertFalse(
                validate_mod.validate_apply_plan(
                    {"files_to_modify": ["agents/other.md"], "steps": [{"upgrade_id": "u2", "file": "agents/other.md"}]},
                    target,
                    proposal,
                    decision,
                )["passed"]
            )
            self.assertFalse(
                validate_mod.validate_apply_plan(
                    {"files_to_modify": ["README.md"], "steps": [{"upgrade_id": "u1", "file": "README.md"}]},
                    target,
                    proposal,
                    decision,
                )["passed"]
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

