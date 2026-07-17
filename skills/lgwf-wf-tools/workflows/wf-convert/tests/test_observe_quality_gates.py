from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def load_module(relative_path: str, name: str):
    path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_index() -> dict:
    return {
        "files": [
            {"path": "README.md"},
            {"path": "flow/workflow.lgwf"},
            {"path": "flow/agents/inspect.md"},
        ]
    }


def valid_business_contract() -> dict:
    return {
        "goal": "分析源 workflow",
        "inputs": [],
        "outputs": [],
        "stages": [
            {
                "rule_id": "stage_rule_001",
                "statement": "先索引后分析",
                "source_files": ["README.md", "flow/workflow.lgwf"],
                "evidence_strength": "high",
            }
        ],
        "decision_rules": [],
        "approval_points": [],
        "error_paths": [],
        "invariants": [],
    }


def valid_inspection() -> dict:
    return {
        "source_summary": [
            {"path": "README.md", "role": "入口说明", "evidence": "说明 workflow 目标"}
        ],
        "detected_stages": [
            {
                "stage_id": "discover",
                "name": "发现",
                "responsibility": "索引源文件",
                "inputs": ["目录"],
                "outputs": ["索引"],
                "source_files": ["README.md", "flow/workflow.lgwf"],
                "evidence_strength": "high",
                "proposal_consumer": ["raw_intent", "stages"],
                "degrade_target": "none",
                "evidence_summary": "入口文件声明了发现阶段",
            }
        ],
        "prompt_contracts": [
            {
                "prompt_path": "flow/agents/inspect.md",
                "responsibility": "分析职责",
                "inputs": ["源文件"],
                "outputs": ["摘要"],
                "constraints": ["不修改源目录"],
                "source_files": ["flow/agents/inspect.md"],
                "evidence_strength": "high",
                "proposal_consumer": ["prompt_contracts"],
                "degrade_target": "none",
                "evidence_summary": "prompt 明确声明分析职责",
            }
        ],
        "source_business_contract": valid_business_contract(),
        "prompt_execution_mechanics": [],
        "presentation_constraints": [],
        "discarded_prompt_techniques": [],
        "human_approval_points": [],
        "gaps": [],
        "risks": [],
        "assumptions": [],
    }


def valid_proposal() -> dict:
    return {
        "workflow_name": "converted-workflow",
        "target_package_root": "skills/converted-workflow",
        "raw_intent": "创建一个先索引源文件、再分析职责并交给人工确认的 LGWF workflow。",
        "source_root": "skills/source-workflow",
        "stages": [
            {
                "stage_id": "discover",
                "name": "发现",
                "responsibility": "索引源文件",
                "inputs": ["目录"],
                "outputs": ["索引"],
                "source_files": ["README.md", "flow/workflow.lgwf"],
                "evidence_strength": "high",
                "evidence_summary": "入口文件声明了发现阶段",
            }
        ],
        "prompt_contracts": [
            {
                "prompt_path": "flow/agents/inspect.md",
                "responsibility": "分析职责",
                "inputs": ["源文件"],
                "outputs": ["摘要"],
                "constraints": ["不修改源目录"],
                "source_files": ["flow/agents/inspect.md"],
                "evidence_strength": "high",
                "evidence_summary": "prompt 明确声明分析职责",
            }
        ],
        "source_business_contract": valid_business_contract(),
        "prompt_execution_mechanics": [],
        "presentation_constraints": [],
        "discarded_prompt_techniques": [],
        "conversion_mapping": [
            {
                "mapping_id": "mapping_001",
                "source_rule_ids": ["stage_rule_001"],
                "mapping_type": "convert_to_lgwf_node",
                "target_design": "discover node",
                "rationale": "保留业务顺序",
            }
        ],
        "parity_requirements": [
            {
                "requirement_id": "parity_001",
                "source_rule_ids": ["stage_rule_001"],
                "description": "保持先索引后分析",
                "verification": "检查节点顺序",
            }
        ],
        "human_approval_points": ["confirm_create_input"],
        "assumptions": [],
        "out_of_scope": ["不直接生成最终 package"],
        "run_workflow_notes_for_wf_create_fast": [],
    }


class InspectionValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "wf/04_confirm_business_flow/inspect_prompt_workflow_react/scripts/validate.py",
            "validate_inspection_for_tests",
        )

    def test_valid_inspection_has_no_static_issues(self):
        self.assertEqual(self.module.validate_inspection(valid_inspection(), valid_index()), [])

    def test_missing_evidence_and_unknown_source_are_blocking(self):
        inspection = valid_inspection()
        inspection["detected_stages"][0].pop("evidence_summary")
        inspection["detected_stages"][0]["source_files"] = ["missing.md"]
        issues = self.module.validate_inspection(inspection, valid_index())
        codes = {item["code"] for item in issues}
        self.assertIn("MISSING_REQUIRED_FIELD", codes)
        self.assertIn("MISSING_EVIDENCE_SUMMARY", codes)
        self.assertIn("SOURCE_PATH_NOT_INDEXED", codes)
        self.assertTrue(all(item["blocking"] for item in issues))


class ProposalValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "wf/04_confirm_business_flow/propose_create_input_react/scripts/validate.py",
            "validate_create_input_for_tests",
        )

    def test_valid_proposal_has_no_static_issues(self):
        self.assertEqual(self.module.validate_create_input(valid_proposal(), valid_inspection()), [])

    def test_mapping_and_parity_must_cover_business_rules(self):
        proposal = valid_proposal()
        proposal["conversion_mapping"] = []
        proposal["parity_requirements"] = []
        issues = self.module.validate_create_input(proposal, valid_inspection())
        codes = {item["code"] for item in issues}
        self.assertIn("UNMAPPED_BUSINESS_RULE", codes)
        self.assertIn("MISSING_PARITY_COVERAGE", codes)

    def test_target_package_root_guardrails(self):
        for value in ("", ".", "../outside", "inside/.lgwf/state", "https://example.com/wf"):
            with self.subTest(value=value):
                self.assertFalse(self.module.has_valid_target_package_root(value))
        for value in ("skills/example", "C:/absolute/example", "/absolute/example"):
            with self.subTest(value=value):
                self.assertTrue(self.module.has_valid_target_package_root(value))


class ObserveProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_module(
            "wf/shared/scripts/observe_protocol.py",
            "observe_protocol_for_tests",
        )

    def test_merge_preserves_python_and_codex_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.json"
            artifact.write_text("{}\n", encoding="utf-8")
            python_report = self.protocol.build_observer_report(
                stage="proposal",
                observer="python",
                issues=[
                    self.protocol.make_issue(
                        observer="python",
                        code="STATIC",
                        field="field",
                        blocking=True,
                        severity="high",
                        issue="静态问题",
                        required_change="修复静态问题",
                    )
                ],
            )
            codex_report = self.protocol.build_observer_report(
                stage="proposal",
                observer="codex",
                issues=[
                    self.protocol.make_issue(
                        observer="codex",
                        code="SEMANTIC",
                        field="raw_intent",
                        blocking=False,
                        severity="low",
                        issue="语义提醒",
                        required_change="交给人工关注",
                    )
                ],
            )
            python_path = root / "python.json"
            codex_path = root / "codex.json"
            python_path.write_text(json.dumps(python_report, ensure_ascii=False), encoding="utf-8")
            codex_path.write_text(json.dumps(codex_report, ensure_ascii=False), encoding="utf-8")
            merged = self.protocol.merge_observer_reports(
                stage="proposal",
                artifact_path=artifact,
                python_report_path=python_path,
                codex_report_path=codex_path,
            )
            self.assertTrue(merged["blocking"])
            self.assertEqual(merged["verdict"], "revise")
            self.assertEqual({item["observer"] for item in merged["issues"]}, {"python", "codex"})

    def test_missing_observer_report_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.json"
            artifact.write_text("{}\n", encoding="utf-8")
            merged = self.protocol.merge_observer_reports(
                stage="inspection",
                artifact_path=artifact,
                python_report_path=root / "missing-python.json",
                codex_report_path=root / "missing-codex.json",
            )
            self.assertTrue(merged["blocking"])
            self.assertTrue(all(item["observer"] == "protocol" for item in merged["issues"]))


if __name__ == "__main__":
    unittest.main()
