from __future__ import annotations

import json
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SELF_IMPROVE_ROOT = PACKAGE_ROOT / "self-improve"


class GitDiffBriefSelfImproveModuleTests(unittest.TestCase):
    def test_self_improve_module_core_files_exist(self) -> None:
        required = [
            "manifest.json",
            "AGENTS.md",
            "README.md",
            "evals/baseline-cases.json",
            "scripts/self_improve.py",
            "scripts/run_self_evals.py",
            "scripts/run_trace_eval.py",
            "scripts/check_self_improve.py",
            "scripts/record_incident.py",
            "scripts/create_proposal.py",
            "scripts/generate_scorecard.py",
            "scripts/_paths.py",
            "templates/proposal.template.md",
        ]

        missing = [relative for relative in required if not (SELF_IMPROVE_ROOT / relative).is_file()]

        self.assertEqual([], missing)

    def test_manifest_declares_static_trace_readiness_mode(self) -> None:
        manifest = json.loads((SELF_IMPROVE_ROOT / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual("static_trace_readiness", manifest["trace_eval_mode"])
        self.assertEqual("scripts/self_improve.py", manifest["entrypoint"])
        self.assertEqual(".local/self-improve", manifest["local_state_root"])

    def test_trace_eval_script_does_not_run_full_runtime_by_default(self) -> None:
        script = (SELF_IMPROVE_ROOT / "scripts/run_trace_eval.py").read_text(encoding="utf-8")

        self.assertIn("static_trace_readiness", script)
        self.assertIn("lgwf_dsl.cli", script)
        self.assertIn("audit", script)
        self.assertIn("compile", script)
        self.assertNotIn("lgwf_client.cli", script)
        self.assertNotIn("--input-json", script)


if __name__ == "__main__":
    unittest.main()
