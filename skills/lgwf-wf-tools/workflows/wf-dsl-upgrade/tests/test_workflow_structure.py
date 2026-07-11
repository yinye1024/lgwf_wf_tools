from __future__ import annotations

import re
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"
STAGE_DIRS = (
    "01_collect_targets",
    "02_confirm_scope",
    "03_upgrade_one_target",
    "04_summarize_upgrade_result",
)
ALLOWED_WF_ROOT_ENTRIES = {
    "workflow.lgwf",
    "artifact_contracts.json",
    "docs",
    "shared",
    *STAGE_DIRS,
}


class WorkflowStructureTest(unittest.TestCase):
    def test_root_contract_files_exist(self) -> None:
        for relative in (
            "AGENTS.md",
            "README.md",
            "entry_contract.json",
            "wf/workflow.lgwf",
            "wf/artifact_contracts.json",
            "wf/shared/scripts/dsl_upgrade_common.py",
            "wf/03_upgrade_one_target/scripts/dsl_upgrade_common.py",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((PACKAGE_ROOT / relative).exists(), relative)

    def test_stage_directories_are_self_contained(self) -> None:
        for stage in STAGE_DIRS:
            stage_root = WF_ROOT / stage
            with self.subTest(stage=stage):
                self.assertTrue((stage_root / "workflow.lgwf").exists())
                self.assertTrue((stage_root / "agents").is_dir())
                self.assertTrue((stage_root / "scripts").is_dir())
                self.assertTrue((stage_root / "resources").is_dir())

    def test_wf_root_has_no_obsolete_stage_directories(self) -> None:
        actual = {path.name for path in WF_ROOT.iterdir()}
        self.assertEqual(actual, ALLOWED_WF_ROOT_ENTRIES)

    def test_root_workflow_only_references_first_layer_stage_workflows(self) -> None:
        workflow_path = WF_ROOT / "workflow.lgwf"
        text = workflow_path.read_text(encoding="utf-8")
        referenced = re.findall(r'WORKFLOW "([^"]+)"', text)
        for relative in referenced:
            with self.subTest(relative=relative):
                self.assertFalse(Path(relative).is_absolute())
                self.assertNotIn("..", Path(relative).parts)
        stage_workflows = {f"{stage}/workflow.lgwf" for stage in STAGE_DIRS}
        self.assertTrue(stage_workflows.issubset(set(referenced)))
        self.assertIn("FOREACH upgrade_each", text)
        self.assertIn("FAIL collect", text)
        self.assertIn('RUN_WORKFLOW "03_upgrade_one_target/workflow.lgwf"', text)
        self.assertNotIn("STEP batch_audit", text)
        self.assertNotIn("STEP classify_findings", text)
        self.assertNotIn("STEP build_upgrade_plan", text)
        self.assertNotIn("STEP apply_upgrade_rules", text)

    def test_per_target_workflow_contains_repair_loop(self) -> None:
        text = (WF_ROOT / "03_upgrade_one_target" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY prepare_repair_context", text)
        self.assertIn("PY audit_current_target", text)
        self.assertIn("REACT repair_target MAX 3", text)
        self.assertIn("OBSERVE PY", text)
        self.assertIn('SCRIPT "scripts/observe_repair.py"', text)
        self.assertNotIn("OBSERVE CODEX", text)
        self.assertIn("DECIDE PY", text)
        self.assertIn("PY finalize_target", text)

    def test_step_docs_are_mirrored_under_target_package(self) -> None:
        expected = {
            "define-shared-helper-and-verification.md",
            "collect-authorized-targets.md",
            "confirm-scope.md",
            "upgrade-one-target.md",
            "summarize-upgrade-result.md",
            "orchestrate-thin-root-workflow.md",
        }
        actual = {path.name for path in (WF_ROOT / "docs" / "steps").glob("*.md")}
        self.assertEqual(actual, expected)
        for name in sorted(expected):
            with self.subTest(name=name):
                self.assertTrue((WF_ROOT / "docs" / "steps" / name).exists(), name)

    def test_agent_prompts_encode_upgrade_safety_boundaries(self) -> None:
        prompts = {
            "confirm_scope": (WF_ROOT / "02_confirm_scope" / "agents" / "confirm_scope.md").read_text(
                encoding="utf-8"
            ),
            "repair_spec": (WF_ROOT / "03_upgrade_one_target" / "agents" / "repair_spec.md").read_text(
                encoding="utf-8"
            ),
            "reason": (WF_ROOT / "03_upgrade_one_target" / "agents" / "reason.md").read_text(encoding="utf-8"),
            "act": (WF_ROOT / "03_upgrade_one_target" / "agents" / "act.md").read_text(encoding="utf-8"),
            "observe": (WF_ROOT / "03_upgrade_one_target" / "agents" / "observe.md").read_text(
                encoding="utf-8"
            ),
        }
        required_terms = {
            "confirm_scope": [
                "范围审批，不是升级计划审批",
                "不会扩大 target_paths",
                "approve 只授权 manifest",
                "reject 不是失败",
            ],
            "repair_spec": [
                "当前 FOREACH item",
                "TARGET_FILES",
                "current_target",
                "dry_run",
                "第 0 次 audit check",
                "CONTRACT {}",
                ".lgwf/",
                "ws/",
                "reports/",
                "LGWF_CONTRACT_REQUIRED_MISSING",
            ],
            "reason": ["不修改文件", "逐条 diagnostics", "修正方案", "LGWF_CONTRACT_REQUIRED_MISSING"],
            "act": ["执行 reason", "diagnostic", "TARGET_FILES", "不要生成临时文件"],
            "observe": ["OBSERVE PY", "audit check", "observe_repair.py"],
        }
        for prompt_name, terms in required_terms.items():
            for term in terms:
                with self.subTest(prompt=prompt_name, term=term):
                    self.assertIn(term, prompts[prompt_name])

        forbidden_terms = [
            "语义上下文不足",
            "保留现状",
            "人工处理",
            "不要猜测修复",
            "需要人工处理",
            "needs_manual_review",
        ]
        for prompt_name in ("repair_spec", "reason", "act"):
            for term in forbidden_terms:
                with self.subTest(prompt=prompt_name, forbidden=term):
                    self.assertNotIn(term, prompts[prompt_name])


if __name__ == "__main__":
    unittest.main()
