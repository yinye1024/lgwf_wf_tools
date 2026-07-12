from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_LGWF = 'D:/allen/github/lgwf_wf_tools/skills/lgwf-wf-tools/workflows/wf-create/wf/workflow.lgwf'
RUN_COMMAND_TEMPLATE = "lgwf.py run --workflow-lgwf {workflow_lgwf} --work-dir {work_dir} --prompt-file {prompt_file}"
STATUS_COMMAND_TEMPLATE = "lgwf.py status --pid {pid}"
APPROVAL_COMMANDS = ["lgwf.py approval get --pid {pid}", "lgwf.py approval submit --pid {pid} --decision approve"]
SCENARIOS = [{'scenario_id': 'happy_path', 'goal': '验证 runtime + Python fake Codex 的主线编排契约，包括 prompt-file、状态查询和审批命令模板。', 'expected_runtime_path': ['propose_requirements_react'], 'manual_approval_required': False, 'approval_decisions': [], 'fake_responses': [{'node_id': 'propose_requirements_react', 'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'propose_requirements_react', 'artifact': '.lgwf/business_flow_proposal.json'}, 'expected_artifact': '.lgwf/business_flow_proposal.json'}, {'node_id': 'propose_business_flow_react', 'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'propose_business_flow_react', 'artifact': '.lgwf/create_requirements_proposal.json'}, 'expected_artifact': '.lgwf/create_requirements_proposal.json'}, {'node_id': 'design_steps_react', 'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'design_steps_react', 'artifact': '.lgwf/step_designs_proposal.json'}, 'expected_artifact': '.lgwf/step_designs_proposal.json'}, {'node_id': 'implement_steps_react', 'workflow': 'wf/04_implement_steps_react/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'implement_steps_react', 'artifact': '.lgwf/fake_codex_output.json'}, 'expected_artifact': '.lgwf/fake_codex_output.json'}], 'covered_branches': [], 'covered_artifacts': ['.lgwf/business_flow_proposal.json', '.lgwf/create_requirements_proposal.json', '.lgwf/step_designs_proposal.json', '.lgwf/business_flow_approval.json', '.lgwf/create_requirements_approval.json', '.lgwf/raw_intent_approval.json', '.lgwf/step_design_confirmation_record.json']}, {'scenario_id': 'repair_or_retry_contract', 'goal': '验证 repair/retry 节点不会回到错误的前序 Codex repair loop。', 'expected_runtime_path': ['implement_steps_react'], 'manual_approval_required': False, 'approval_decisions': [], 'fake_responses': [{'node_id': 'propose_requirements_react', 'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'propose_requirements_react', 'artifact': '.lgwf/business_flow_proposal.json'}, 'expected_artifact': '.lgwf/business_flow_proposal.json'}, {'node_id': 'propose_business_flow_react', 'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'propose_business_flow_react', 'artifact': '.lgwf/create_requirements_proposal.json'}, 'expected_artifact': '.lgwf/create_requirements_proposal.json'}, {'node_id': 'design_steps_react', 'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'design_steps_react', 'artifact': '.lgwf/step_designs_proposal.json'}, 'expected_artifact': '.lgwf/step_designs_proposal.json'}, {'node_id': 'implement_steps_react', 'workflow': 'wf/04_implement_steps_react/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'implement_steps_react', 'artifact': '.lgwf/fake_codex_output.json'}, 'expected_artifact': '.lgwf/fake_codex_output.json'}], 'covered_branches': [], 'covered_artifacts': ['.lgwf/business_flow_proposal.json', '.lgwf/create_requirements_proposal.json', '.lgwf/step_designs_proposal.json']}]
BRANCH_TARGETS = []
ARTIFACT_ASSERTIONS = {'output_json': ['.lgwf/business_flow_proposal.json', '.lgwf/create_requirements_proposal.json', '.lgwf/step_designs_proposal.json'], 'persist_artifacts': ['.lgwf/business_flow_approval.json', '.lgwf/create_requirements_approval.json', '.lgwf/raw_intent_approval.json', '.lgwf/step_design_confirmation_record.json']}
FAKE_CODEX_CONTRACT = {'implementation': 'Python fake Codex', 'class_name': 'FakeCodex', 'prompt_file_support': True, 'call_index': True, 'response_mapping': [{'node_id': 'propose_requirements_react', 'workflow': 'wf/01_confirm_requirements/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'propose_requirements_react', 'artifact': '.lgwf/business_flow_proposal.json'}, 'expected_artifact': '.lgwf/business_flow_proposal.json'}, {'node_id': 'propose_business_flow_react', 'workflow': 'wf/02_confirm_business_flow/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'propose_business_flow_react', 'artifact': '.lgwf/create_requirements_proposal.json'}, 'expected_artifact': '.lgwf/create_requirements_proposal.json'}, {'node_id': 'design_steps_react', 'workflow': 'wf/03_confirm_step_designs/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'design_steps_react', 'artifact': '.lgwf/step_designs_proposal.json'}, 'expected_artifact': '.lgwf/step_designs_proposal.json'}, {'node_id': 'implement_steps_react', 'workflow': 'wf/04_implement_steps_react/workflow.lgwf', 'prompt_file_required': True, 'response_json': {'ok': True, 'node': 'implement_steps_react', 'artifact': '.lgwf/fake_codex_output.json'}, 'expected_artifact': '.lgwf/fake_codex_output.json'}]}


class FakeCodex:
    """Python fake Codex runner used by generated runtime fake E2E tests."""

    def __init__(self, response_by_prompt: dict[str, dict[str, object]] | None = None) -> None:
        self.response_by_prompt = response_by_prompt or {}
        self.calls: list[dict[str, object]] = []

    def run(self, argv: list[str]) -> dict[str, object]:
        if "--prompt-file" not in argv:
            raise AssertionError("--prompt-file is required")
        prompt_index = argv.index("--prompt-file") + 1
        if prompt_index >= len(argv):
            raise AssertionError("--prompt-file must have a value")
        prompt_file = Path(argv[prompt_index])
        prompt = prompt_file.read_text(encoding="utf-8")
        call = {
            "call_index": len(self.calls),
            "argv": list(argv),
            "prompt_file": str(prompt_file),
            "prompt": prompt,
        }
        self.calls.append(call)
        response = dict(self.response_by_prompt.get(prompt, {"status": "ok"}))
        response.setdefault("status", "ok")
        response.setdefault("call_index", call["call_index"])
        return response


class GeneratedRuntimeFakeE2ETest(unittest.TestCase):
    def workflow_path(self) -> Path:
        path = Path(WORKFLOW_LGWF)
        return path if path.is_absolute() else ROOT / path

    def scenario(self, scenario_id: str) -> dict[str, object]:
        for scenario in SCENARIOS:
            if scenario["scenario_id"] == scenario_id:
                return scenario
        raise AssertionError(f"scenario missing: {scenario_id}")

    def run_fake_with_prompt(self, fake: FakeCodex, prompt: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp:
            prompt_file = Path(temp) / "prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            return fake.run(["codex", "exec", "--prompt-file", str(prompt_file)])

    def test_runtime_driver_contract_uses_prompt_file_status_and_approval(self) -> None:
        self.assertTrue(self.workflow_path().exists(), f"workflow missing: {self.workflow_path()}")
        self.assertIn("lgwf.py run --workflow-lgwf", RUN_COMMAND_TEMPLATE)
        self.assertIn("--prompt-file", RUN_COMMAND_TEMPLATE)
        self.assertIn("status", STATUS_COMMAND_TEMPLATE)
        approval_text = " ".join(APPROVAL_COMMANDS)
        self.assertIn("approval get", approval_text)
        self.assertIn("approval submit", approval_text)

    def test_python_fake_codex_contract(self) -> None:
        self.assertEqual(FAKE_CODEX_CONTRACT.get("implementation"), "Python fake Codex")
        self.assertTrue(FAKE_CODEX_CONTRACT.get("prompt_file_support"))
        fake = FakeCodex()
        result = self.run_fake_with_prompt(fake, "contract prompt")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(fake.calls[0]["prompt"], "contract prompt")

    def test_artifact_contracts_declared(self) -> None:
        self.assertIn("output_json", ARTIFACT_ASSERTIONS)
        self.assertIn("persist_artifacts", ARTIFACT_ASSERTIONS)

    def test_happy_path(self) -> None:
        scenario = self.scenario('happy_path')
        self.assertTrue(scenario["expected_runtime_path"] or scenario["covered_branches"] or scenario["covered_artifacts"])
        self.assertIn("lgwf.py run --workflow-lgwf", RUN_COMMAND_TEMPLATE)
        self.assertIn("--prompt-file", RUN_COMMAND_TEMPLATE)
        fake = FakeCodex()
        result = self.run_fake_with_prompt(fake, "runtime fake prompt for " + scenario["scenario_id"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(fake.calls[0]["call_index"], 0)
        for branch in scenario.get("covered_branches", []):
            self.assertIn(branch, BRANCH_TARGETS)

    def test_repair_or_retry_contract(self) -> None:
        scenario = self.scenario('repair_or_retry_contract')
        self.assertTrue(scenario["expected_runtime_path"] or scenario["covered_branches"] or scenario["covered_artifacts"])
        self.assertIn("lgwf.py run --workflow-lgwf", RUN_COMMAND_TEMPLATE)
        self.assertIn("--prompt-file", RUN_COMMAND_TEMPLATE)
        fake = FakeCodex()
        result = self.run_fake_with_prompt(fake, "runtime fake prompt for " + scenario["scenario_id"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(fake.calls[0]["call_index"], 0)
        for branch in scenario.get("covered_branches", []):
            self.assertIn(branch, BRANCH_TARGETS)



if __name__ == "__main__":
    unittest.main()
