from __future__ import annotations

import json
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class RegistryAndArtifactContractTests(unittest.TestCase):
    def test_entry_contract_matches_expected_paths(self) -> None:
        contract = json.loads((PACKAGE_ROOT / "entry_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["id"], "wf-maintenance-gate")
        self.assertEqual(contract["workflow_lgwf"], "skills/lgwf-wf-tools/workflows/wf-maintenance-gate/wf/workflow.lgwf")
        self.assertEqual(contract["work_dir"], "skills/lgwf-wf-tools/workflows/wf-maintenance-gate/ws")
        self.assertEqual(contract["auto_human_policy"], "forbidden")

    def test_artifact_contract_declares_summary_outputs(self) -> None:
        artifact_contracts = json.loads((PACKAGE_ROOT / "wf" / "artifact_contracts.json").read_text(encoding="utf-8"))
        final_outputs = artifact_contracts["final_outputs"]
        self.assertIn(".lgwf/maintenance_gate_summary.json", final_outputs)
        self.assertIn("reports/wf-maintenance-gate/report.md", final_outputs)


if __name__ == "__main__":
    unittest.main()
