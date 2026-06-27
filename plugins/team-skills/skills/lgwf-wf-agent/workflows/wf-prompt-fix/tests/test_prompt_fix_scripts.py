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


class PromptFixScriptsTest(unittest.TestCase):
    def test_prompt_fix_workflow_uses_owned_namespace_and_react(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("WORKFLOW lgwf_wf_prompt_fix;", source)
        self.assertIn("ENTRY init_prompt_fix_target;", source)
        self.assertIn("APPROVAL init_prompt_fix_target", source)
        self.assertIn("READ state.prompt_fix_target", source)
        self.assertIn("WRITE state.lgwf_wf_prompt_fix.prompt_fix_target", source)
        self.assertIn('PERSIST ".lgwf/prompt_fix_target.json"', source)
        self.assertIn("PY check_lgwf_client_assist", source)
        self.assertIn('SCRIPT "00_check_environment/scripts/check_lgwf_client_assist.py"', source)
        self.assertIn("lgwf_wf_prompt_fix.prompt_acceptance.instructions.{node}", source)
        for artifact in (
            ".lgwf/prompt_fix_target.json",
            ".lgwf/prompt_acceptance/inventory.json",
            ".lgwf/prompt_acceptance/audit.json",
            ".lgwf/prompt_acceptance/fix_selection.json",
            ".lgwf/prompt_acceptance/repair_plan.json",
            ".lgwf/prompt_acceptance/repair_review.json",
            ".lgwf/prompt_acceptance/react_history.json",
        ):
            self.assertIn(artifact, source)
        self.assertNotIn(".lgwf/prompt_acceptance/fix_notes.md", source)
        self.assertIn("CODEX audit_target_prompts", source)
        self.assertIn("APPROVAL select_prompt_fixes", source)
        self.assertIn("REACT repair_target_prompts MAX 3", source)
        self.assertIn("APPROVAL confirm_prompt_acceptance", source)
        self.assertIn("PY route_after_prompt_acceptance_summary", source)
        self.assertIn("PY finish_prompt_acceptance", source)
        self.assertIn("FLOW init_prompt_fix_target", source)
        self.assertIn("THEN check_lgwf_client_assist", source)
        self.assertIn("THEN build_prompt_inventory", source)
        self.assertIn("CONTEXT workspace file \".lgwf/prompt_fix_target.json\"", source)
        self.assertIn('WHEN "fix" THEN repair_target_prompts', source)
        self.assertIn('WHEN "summarize" THEN summarize_prompt_acceptance', source)
        self.assertIn('WHEN "auto_finish" THEN finish_prompt_acceptance', source)
        self.assertIn('WHEN "confirm" THEN confirm_prompt_acceptance', source)
        self.assertNotIn("THEN route_after_prompt_acceptance_summary\n  THEN confirm_prompt_acceptance", source)

    def test_environment_check_detects_missing_and_present_skill(self) -> None:
        check_mod = load_module(
            "00_check_environment/scripts/check_lgwf_client_assist.py",
            "prompt_env_check",
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
            "prompt_env_check_legacy_marker",
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
            "prompt_inventory",
        )
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "target"
            nested = package / "child"
            prompt = nested / "agents" / "prompt.md"
            approval = package / "approve.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("# Role\nDo work.\n", encoding="utf-8")
            approval.write_text("确认。", encoding="utf-8")
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
        self.assertTrue(all(item["artifact_root"] == ".lgwf/prompt_acceptance" for item in inventory["prompts"]))

    def test_prompt_inventory_excludes_runtime_and_cache_dirs(self) -> None:
        inventory_mod = load_module(
            "01_inventory/scripts/build_prompt_inventory.py",
            "prompt_inventory_exclusions",
        )
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "target"
            package.mkdir()
            (package / "prompt.md").write_text("# Role\nDo work.\n", encoding="utf-8")
            (package / "workflow.lgwf").write_text(
                'WORKFLOW root;\nCODEX audit\n  PROMPT "prompt.md";\n',
                encoding="utf-8",
            )
            runtime = package / ".lgwf" / "workflow"
            runtime.mkdir(parents=True)
            (runtime / "runtime_prompt.md").write_text("# Role\nIgnore.\n", encoding="utf-8")
            (runtime / "workflow.lgwf").write_text(
                'WORKFLOW runtime;\nCODEX audit\n  PROMPT "runtime_prompt.md";\n',
                encoding="utf-8",
            )
            inventory = inventory_mod.build_prompt_inventory(package / "workflow.lgwf", package)
        self.assertEqual([item["workflow_path"] for item in inventory["prompts"]], ["workflow.lgwf"])

    def test_prompt_inventory_resolves_target_paths_from_workspace_ancestors(self) -> None:
        inventory_mod = load_module(
            "01_inventory/scripts/build_prompt_inventory.py",
            "prompt_inventory_relative_target",
        )
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            work_dir = repo / "plugins" / "skill" / "ws"
            package = repo / "target"
            work_dir.mkdir(parents=True)
            package.mkdir()
            workflow = package / "workflow.lgwf"
            prompt = package / "prompt.md"
            workflow.write_text('WORKFLOW root;\nCODEX audit\n  PROMPT "prompt.md";\n', encoding="utf-8")
            prompt.write_text("# Role\nDo work.\n", encoding="utf-8")
            resolved = inventory_mod.resolve_target_path("target/workflow.lgwf", work_dir)
        self.assertEqual(resolved, workflow.resolve())

    def test_prompt_fix_selection_supports_all_partial_and_skip(self) -> None:
        selection_mod = load_module(
            "03_select_prompt_fixes/scripts/validate_prompt_fix_selection.py",
            "prompt_selection",
        )
        audit = {"issues": [{"id": "p1"}, {"id": "p2"}]}
        self.assertEqual(selection_mod.normalize_selection({"fix_all": True}, audit)["selected_issue_ids"], ["p1", "p2"])
        self.assertEqual(
            selection_mod.normalize_selection({"selected_issue_ids": ["p2", "missing"]}, audit)["selected_issue_ids"],
            ["p2"],
        )
        skipped = selection_mod.normalize_selection({"skip_fix": True, "comment": "later"}, audit)
        self.assertTrue(skipped["skip_fix"])
        self.assertEqual(selection_mod.choose_route(skipped, audit), "summarize")
        self.assertEqual(selection_mod.choose_route({"selected_issue_ids": ["p1"]}, audit), "fix")

    def test_prompt_fix_selection_context_groups_file_results_and_issues(self) -> None:
        context_mod = load_module(
            "03_select_prompt_fixes/scripts/prepare_prompt_fix_selection_context.py",
            "prompt_selection_context",
        )
        audit = {
            "passed": False,
            "prompt_count": 2,
            "file_results": [
                {
                    "prompt_path": "agents/passed.md",
                    "workflow_path": "workflow.lgwf",
                    "node_id": "passed_node",
                    "react_phase": "",
                    "prompt_type": "Normal",
                    "passed": True,
                    "checked_dimensions": ["routing", "shared_rules"],
                    "issue_ids": [],
                    "summary": "通过。",
                },
                {
                    "prompt_path": "agents/failed.md",
                    "workflow_path": "workflow.lgwf",
                    "node_id": "failed_node",
                    "react_phase": "observe",
                    "prompt_type": "Audit",
                    "passed": False,
                    "checked_dimensions": ["audit_scope", "output_format"],
                    "issue_ids": ["prompt_issue_1"],
                    "summary": "缺少稳定输出格式。",
                },
            ],
            "issues": [
                {
                    "id": "prompt_issue_1",
                    "prompt_path": "agents/failed.md",
                    "severity": "high",
                    "problem": "缺少 Output Format。",
                }
            ],
        }
        inventory = {"prompts": [{"prompt_path": "agents/passed.md"}, {"prompt_path": "agents/failed.md"}]}

        context = context_mod.build_context(audit, inventory)

        self.assertFalse(context["audit_passed"])
        self.assertEqual(context["prompt_count"], 2)
        self.assertEqual(len(context["file_results"]), 2)
        self.assertEqual([item["prompt_path"] for item in context["files_passed"]], ["agents/passed.md"])
        self.assertEqual([item["prompt_path"] for item in context["files_with_issues"]], ["agents/failed.md"])
        self.assertEqual(context["files_with_issues"][0]["issues"][0]["id"], "prompt_issue_1")
        self.assertEqual(context["issues_by_prompt_path"]["agents/failed.md"][0]["id"], "prompt_issue_1")

    def test_prompt_fix_selection_context_falls_back_without_file_results(self) -> None:
        context_mod = load_module(
            "03_select_prompt_fixes/scripts/prepare_prompt_fix_selection_context.py",
            "prompt_selection_context_fallback",
        )
        audit = {
            "passed": False,
            "issues": [
                {
                    "id": "prompt_issue_1",
                    "prompt_path": "agents/failed.md",
                    "severity": "high",
                }
            ],
        }

        context = context_mod.build_context(audit, {"prompts": []})

        self.assertEqual(context["file_results"], [])
        self.assertEqual(context["issues_by_prompt_path"]["agents/failed.md"][0]["id"], "prompt_issue_1")
        self.assertEqual(context["files_with_issues"][0]["prompt_path"], "agents/failed.md")
        self.assertEqual(context["files_with_issues"][0]["issue_ids"], ["prompt_issue_1"])

    def test_audit_prompt_requires_file_results_for_every_inventory_prompt(self) -> None:
        source = (ROOT / "wf" / "02_audit_prompts" / "agents" / "audit_target_prompts.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("file_results", source)
        self.assertIn("prompt_count", source)
        self.assertIn("checked_dimensions", source)
        self.assertIn("通过", source)
        self.assertIn("inventory.prompts[]", source)

    def test_select_prompt_fixes_prompts_for_file_grouped_confirmation(self) -> None:
        source = (ROOT / "wf" / "03_select_prompt_fixes" / "select_prompt_fixes.md").read_text(encoding="utf-8")
        self.assertIn("file_results", source)
        self.assertIn("files_with_issues", source)
        self.assertIn("files_passed", source)
        self.assertIn("fix_all=true", source)

    def test_prompt_react_decide_exits_only_when_selected_issues_pass(self) -> None:
        decide_mod = load_module(
            "04_repair_prompts/scripts/decide_prompt_fix.py",
            "prompt_decide",
        )
        selection = {"selected_issue_ids": ["p1", "p2"], "skip_fix": False}
        self.assertEqual(
            decide_mod.choose_next(selection, {"passed": True, "remaining_issue_ids": []}),
            "exit",
        )
        self.assertEqual(
            decide_mod.choose_next(selection, {"passed": False, "remaining_issue_ids": ["p2"]}),
            "continue",
        )

    def test_prompt_acceptance_summary_promotes_only_final_root_artifact(self) -> None:
        summary_mod = load_module(
            "05_summary/scripts/summarize_prompt_acceptance.py",
            "prompt_summary",
        )
        summary = summary_mod.build_summary(
            inventory={"prompts": [{"prompt_path": "agents/prompt.md"}]},
            audit={"passed": False, "issues": [{"id": "p1", "severity": "high"}]},
            selection={"selected_issue_ids": ["p1"], "skip_fix": False},
            review={"passed": True, "remaining_issue_ids": []},
            history=[{"next": "exit"}],
        )
        self.assertEqual(summary["artifact_root"], ".lgwf/prompt_acceptance")
        self.assertEqual(summary["root_summary_path"], ".lgwf/target_prompt_acceptance_summary.json")
        self.assertEqual(summary["status"], "fixed")
        self.assertEqual(summary["prompt_count"], 1)
        self.assertEqual(summary["selected_issue_ids"], ["p1"])

    def test_prompt_acceptance_summary_route_auto_finishes_clean_repair_only(self) -> None:
        route_mod = load_module(
            "05_summary/scripts/route_after_prompt_acceptance_summary.py",
            "prompt_summary_route",
        )
        self.assertEqual(
            route_mod.choose_route(
                {
                    "status": "fixed",
                    "repair_passed": True,
                    "remaining_issue_ids": [],
                }
            ),
            "auto_finish",
        )
        self.assertEqual(
            route_mod.choose_route(
                {
                    "status": "fixed",
                    "repair_passed": True,
                    "remaining_issue_ids": ["p2"],
                }
            ),
            "confirm",
        )
        self.assertEqual(
            route_mod.choose_route(
                {
                    "status": "fixed",
                    "repair_passed": True,
                    "remaining_issue_ids": [],
                    "unexpected_changes": ["wf/workflow.lgwf"],
                }
            ),
            "confirm",
        )

    def test_prompt_acceptance_auto_finish_writes_confirmation_contract(self) -> None:
        finish_mod = load_module(
            "05_summary/scripts/finish_prompt_acceptance.py",
            "prompt_summary_finish",
        )
        confirmation = finish_mod.build_confirmation({"status": "fixed", "remaining_issue_ids": []})
        self.assertTrue(confirmation["confirmed"])
        self.assertTrue(confirmation["auto_confirmed"])
        self.assertEqual(confirmation["status"], "fixed")
        self.assertEqual(confirmation["remaining_issue_ids"], [])


if __name__ == "__main__":
    unittest.main()
