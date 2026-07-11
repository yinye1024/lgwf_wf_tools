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
    import sys

    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class RuntimeFakeE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.collect = load_module("01_collect_targets/scripts/collect_targets.py", "collect_targets_fake_e2e")
        cls.scope_prepare = load_module(
            "02_confirm_scope/scripts/prepare_scope_confirmation.py",
            "scope_prepare_fake_e2e",
        )
        cls.scope_route = load_module("02_confirm_scope/scripts/route_scope_decision.py", "scope_route_fake_e2e")
        cls.repair_prepare = load_module(
            "03_upgrade_one_target/scripts/prepare_repair_context.py",
            "repair_prepare_fake_e2e",
        )
        cls.audit = load_module("03_upgrade_one_target/scripts/audit_current_target.py", "audit_target_fake_e2e")
        cls.finalize = load_module("03_upgrade_one_target/scripts/finalize_target.py", "finalize_fake_e2e")
        cls.summary = load_module("04_summarize_upgrade_result/scripts/summarize_upgrade_result.py", "summary_fake_e2e")

    def make_target(self, root: Path) -> Path:
        allowed = root / "allowed"
        allowed.mkdir()
        target = allowed / "workflow.lgwf"
        target.write_text("WORKFLOW demo;\nENTRY FLOW main;\nFLOW main START done;\n", encoding="utf-8")
        return target

    def test_rejected_scope_goes_to_summary_without_target_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = self.make_target(root)
            collect_result = self.collect.collect_targets_from_request(
                root,
                {
                    "dsl_upgrade_target": {
                        "target_paths": [str(target)],
                        "allowed_dirs": [str(target.parent)],
                        "mode": "apply",
                        "scope_mode": "explicit",
                    }
                },
            )
            self.assertTrue(collect_result["validation"]["passed"])
            self.scope_prepare.build_scope_confirmation_context(root)
            write_json(root / ".lgwf" / "scope_approval.json", {"decision": "reject"})

            route = self.scope_route.choose_scope_route(root, {"decision": "reject"})
            summary = self.summary.build_result_summary(root, {"target_results": []})

            self.assertEqual(route, "summary")
            self.assertEqual(summary["status"], "skipped")

    def test_approved_scope_processes_single_passing_target_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = self.make_target(root)
            collect_result = self.collect.collect_targets_from_request(
                root,
                {
                    "dsl_upgrade_target": {
                        "target_paths": [str(target)],
                        "allowed_dirs": [str(target.parent)],
                        "mode": "apply",
                        "scope_mode": "explicit",
                    }
                },
            )
            current_target = collect_result["state_updates"]["wf_dsl_upgrade.targets"][0]
            self.scope_prepare.build_scope_confirmation_context(root)
            write_json(root / ".lgwf" / "scope_approval.json", {"decision": "approve"})
            self.assertEqual(self.scope_route.choose_scope_route(root, {"decision": "approve"}), "run")

            context = self.repair_prepare.build_repair_context(root, current_target)
            original_audit = self.audit.run_lgwf_audit
            self.audit.run_lgwf_audit = lambda path: {
                "target_path": str(path),
                "returncode": 0,
                "passed": True,
                "diagnostics": [],
            }
            try:
                audit_result = self.audit.audit_target(root, current_target)
            finally:
                self.audit.run_lgwf_audit = original_audit
            self.assertEqual(audit_result["route"], "finalize")
            self.assertEqual(context["target_files"], [str(target.resolve())])

            result = self.finalize.finalize_target(root)
            summary = self.summary.build_result_summary(root, {"target_results": [result]})

            self.assertEqual(result["status"], "passed")
            self.assertEqual(summary["status"], "passed")
            self.assertEqual(summary["passed_target_count"], 1)


if __name__ == "__main__":
    unittest.main()
