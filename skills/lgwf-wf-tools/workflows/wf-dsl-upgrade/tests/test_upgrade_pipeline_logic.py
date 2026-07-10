from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"


def load_module(relative: str, name: str):
    path = WF_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class UpgradePipelineLogicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.collect_module = load_module("01_collect_targets/scripts/collect_targets.py", "collect_targets")
        cls.scope_prepare_module = load_module(
            "02_confirm_scope/scripts/prepare_scope_confirmation.py",
            "prepare_scope_confirmation",
        )
        cls.scope_route_module = load_module(
            "02_confirm_scope/scripts/route_scope_decision.py",
            "route_scope_decision",
        )
        cls.repair_prepare_module = load_module(
            "03_upgrade_one_target/scripts/prepare_repair_context.py",
            "prepare_repair_context",
        )
        cls.decide_module = load_module("03_upgrade_one_target/scripts/decide_next.py", "decide_next")
        cls.finalize_module = load_module("03_upgrade_one_target/scripts/finalize_target.py", "finalize_target")
        cls.summary_module = load_module("04_summarize_upgrade_result/scripts/summarize_upgrade_result.py", "summary")

    def test_collect_targets_rejects_out_of_scope_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "allowed"
            outside = root / "outside"
            allowed.mkdir()
            outside.mkdir()
            target = outside / "workflow.lgwf"
            target.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")

            result = self.collect_module.collect_targets_from_request(
                root,
                {
                    "target_paths": [str(target)],
                    "allowed_dirs": [str(allowed)],
                    "mode": "dry_run",
                    "scope_mode": "explicit",
                    "max_targets": 4,
                },
            )

            self.assertFalse(result["validation"]["passed"])
            self.assertIn("超出 allowed_dirs", "\n".join(result["validation"]["reasons"]))
            self.assertFalse(result["manifest"]["targets"][0]["authorized"])

    def test_collect_targets_expands_directory_to_all_lgwf_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "allowed"
            nested = allowed / "stage"
            nested.mkdir(parents=True)
            root_workflow = allowed / "workflow.lgwf"
            stage_workflow = nested / "analyze.lgwf"
            root_workflow.write_text("WORKFLOW root;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")
            stage_workflow.write_text("WORKFLOW stage;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")

            result = self.collect_module.collect_targets_from_request(
                root,
                {
                    "target_paths": [str(allowed), str(root_workflow)],
                    "allowed_dirs": [str(allowed)],
                    "mode": "dry_run",
                    "scope_mode": "explicit",
                    "max_targets": 8,
                },
            )

            self.assertTrue(result["validation"]["passed"])
            discovered = [item["resolved_path"] for item in result["manifest"]["authorized_targets"]]
            self.assertEqual(discovered, sorted({str(root_workflow.resolve()), str(stage_workflow.resolve())}))
            self.assertEqual(result["manifest"]["target_count"], 2)

    def test_collect_targets_exposes_foreach_state_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "allowed"
            allowed.mkdir()
            target = allowed / "workflow.lgwf"
            target.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")

            result = self.collect_module.collect_targets_from_request(
                root,
                {
                    "target_paths": [str(target)],
                    "allowed_dirs": [str(allowed)],
                    "mode": "apply",
                    "scope_mode": "explicit",
                    "max_targets": 4,
                },
            )

            foreach_targets = result["state_updates"]["wf_dsl_upgrade.targets"]
            self.assertEqual(len(foreach_targets), 1)
            foreach_target = foreach_targets[0]
            self.assertEqual(foreach_target["target_id"], "target_0001")
            self.assertEqual(foreach_target["path"], str(target.resolve()))
            self.assertEqual(foreach_target["target_files"], [str(target.resolve())])
            self.assertEqual(foreach_target["target_dirs"], [str(allowed.resolve())])
            self.assertEqual(foreach_target["mode"], "apply")

    def test_scope_route_requires_approval_validation_and_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "target_manifest.json", {"authorized_targets": [{"resolved_path": "demo.lgwf"}]})
            write_json(lgwf_dir / "target_scope_validation.json", {"passed": True})
            write_json(lgwf_dir / "scope_approval.json", {"decision": "approve"})
            self.assertEqual(self.scope_route_module.choose_scope_route(root), "run")

            write_json(lgwf_dir / "scope_approval.json", {"decision": "reject"})
            self.assertEqual(self.scope_route_module.choose_scope_route(root), "summary")

            write_json(lgwf_dir / "scope_approval.json", {"decision": "approve"})
            write_json(lgwf_dir / "target_scope_validation.json", {"passed": False})
            self.assertEqual(self.scope_route_module.choose_scope_route(root), "summary")

    def test_scope_confirmation_context_summarizes_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_json(
                root / ".lgwf" / "target_manifest.json",
                {
                    "request": {"mode": "apply", "scope_mode": "explicit"},
                    "authorized_targets": [{"resolved_path": "D:/demo/workflow.lgwf", "pre_hash": "abc"}],
                },
            )
            write_json(root / ".lgwf" / "target_scope_validation.json", {"passed": True, "reasons": []})

            context = self.scope_prepare_module.build_scope_confirmation_context(root)

            self.assertEqual(context["mode"], "apply")
            self.assertEqual(context["target_count"], 1)
            self.assertEqual(context["recommended_decision"], "approve")
            self.assertEqual(context["targets"][0]["pre_hash"], "abc")

    def test_prepare_repair_context_limits_codex_to_current_target_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            allowed = root / "allowed"
            allowed.mkdir()
            target = allowed / "workflow.lgwf"
            target.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")

            context = self.repair_prepare_module.build_repair_context(
                root,
                {
                    "target_id": "target_0001",
                    "path": str(target),
                    "mode": "apply",
                    "allowed_dirs": [str(allowed)],
                    "pre_hash": "abc",
                },
            )

            self.assertTrue(context["authorized"])
            self.assertEqual(context["target_files"], [str(target.resolve())])
            self.assertEqual(context["target_dirs"], [str(allowed.resolve())])

    def test_decide_next_retries_failed_audit_and_exits_passed_audit(self) -> None:
        retry = self.decide_module.decide_next({"passed": False, "diagnostics": [{"code": "A"}]})
        self.assertEqual(retry["next"], "continue")
        self.assertEqual(retry["repair_decision"]["status"], "retry")

        done = self.decide_module.decide_next({"passed": True, "diagnostics": []})
        self.assertEqual(done["next"], "exit")
        self.assertEqual(done["repair_decision"]["status"], "passed")

    def test_finalize_target_marks_manual_review_when_apply_still_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "workflow.lgwf"
            target.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")
            write_json(
                root / ".lgwf" / "current_target_context.json",
                {"target_id": "target_0001", "path": str(target), "mode": "apply", "pre_hash": "abc"},
            )
            write_json(
                root / ".lgwf" / "current_target_audit.json",
                {"passed": False, "diagnostics": [{"code": "LGWF_CONTRACT_REQUIRED_MISSING"}]},
            )

            result = self.finalize_module.finalize_target(root)

            self.assertEqual(result["status"], "needs_manual_review")
            self.assertEqual(result["diagnostic_count"], 1)

    def test_summary_counts_foreach_target_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".lgwf").mkdir()
            summary = self.summary_module.build_result_summary(
                root,
                {
                    "target_manifest": {
                        "request": {"mode": "apply", "scope_mode": "explicit"},
                        "target_count": 3,
                        "authorized_targets": [
                            {"resolved_path": "D:/demo/a.lgwf"},
                            {"resolved_path": "D:/demo/b.lgwf"},
                            {"resolved_path": "D:/demo/c.lgwf"},
                        ],
                    },
                    "target_scope_validation": {"passed": True, "reasons": []},
                    "scope_approval": {"decision": "approve"},
                    "target_results": [
                        {"target_path": "D:/demo/a.lgwf", "status": "repaired", "passed": True, "changed": True},
                        {"target_path": "D:/demo/b.lgwf", "status": "passed", "passed": True, "changed": False},
                        {
                            "target_path": "D:/demo/c.lgwf",
                            "status": "needs_manual_review",
                            "passed": False,
                            "diagnostic_count": 2,
                        },
                    ],
                },
            )
            report = self.summary_module.render_report(summary)

            self.assertEqual(summary["status"], "partial")
            self.assertEqual(summary["target_result_count"], 3)
            self.assertEqual(summary["repaired_target_count"], 1)
            self.assertEqual(summary["passed_target_count"], 2)
            self.assertEqual(summary["manual_review_count"], 1)
            self.assertIn("FOREACH 目标结果", report)
            self.assertIn("needs_manual_review", report)

    def test_summary_marks_rejected_apply_as_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".lgwf").mkdir()
            summary = self.summary_module.build_result_summary(
                root,
                {
                    "target_manifest": {
                        "request": {"mode": "apply", "scope_mode": "explicit"},
                        "target_count": 1,
                        "authorized_targets": [{"resolved_path": "D:/demo/workflow.lgwf"}],
                    },
                    "target_scope_validation": {"passed": True, "reasons": []},
                    "scope_approval": {"decision": "reject"},
                    "target_results": [],
                },
            )

            self.assertEqual(summary["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
