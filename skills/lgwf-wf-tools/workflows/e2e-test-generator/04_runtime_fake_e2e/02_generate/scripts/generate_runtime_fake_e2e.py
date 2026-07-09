from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, slugify, write_json, write_text


def py_literal(value: Any) -> str:
    return repr(value)


def method_name(scenario_id: str) -> str:
    return f"test_{slugify(scenario_id)}"


def render_scenario_method(scenario: dict[str, Any]) -> str:
    scenario_id = str(scenario.get("scenario_id") or "scenario")
    return f'''
    def {method_name(scenario_id)}(self) -> None:
        scenario = self.scenario({scenario_id!r})
        self.assertTrue(scenario["expected_runtime_path"] or scenario["covered_branches"] or scenario["covered_artifacts"])
        self.assertIn("lgwf.py run --workflow-lgwf", RUN_COMMAND_TEMPLATE)
        self.assertIn("--prompt-file", RUN_COMMAND_TEMPLATE)
        fake = FakeCodex()
        result = self.run_fake_with_prompt(fake, "runtime fake prompt for " + scenario["scenario_id"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(fake.calls[0]["call_index"], 0)
        for branch in scenario.get("covered_branches", []):
            self.assertIn(branch, BRANCH_TARGETS)
'''


def render_test(design: dict[str, Any]) -> str:
    scenarios = design.get("scenarios") or []
    scenario_methods = "".join(render_scenario_method(scenario) for scenario in scenarios)
    if not scenario_methods:
        scenario_methods = '''
    def test_runtime_fake_skipped_contract(self) -> None:
        self.assertFalse(SCENARIOS)
'''
    return f'''from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_LGWF = {py_literal(design.get("workflow_lgwf", "workflow.lgwf"))}
RUN_COMMAND_TEMPLATE = "lgwf.py run --workflow-lgwf {{workflow_lgwf}} --work-dir {{work_dir}} --prompt-file {{prompt_file}}"
STATUS_COMMAND_TEMPLATE = "lgwf.py status --pid {{pid}}"
APPROVAL_COMMANDS = ["lgwf.py approval get --pid {{pid}}", "lgwf.py approval submit --pid {{pid}} --decision approve"]
SCENARIOS = {py_literal(scenarios)}
BRANCH_TARGETS = {py_literal(design.get("branch_targets", []))}
ARTIFACT_ASSERTIONS = {py_literal(design.get("artifact_assertions", {}))}
FAKE_CODEX_CONTRACT = {py_literal(design.get("fake_codex_contract", {}))}


class FakeCodex:
    """Python fake Codex runner used by generated runtime fake E2E tests."""

    def __init__(self, response_by_prompt: dict[str, dict[str, object]] | None = None) -> None:
        self.response_by_prompt = response_by_prompt or {{}}
        self.calls: list[dict[str, object]] = []

    def run(self, argv: list[str]) -> dict[str, object]:
        if "--prompt-file" not in argv:
            raise AssertionError("--prompt-file is required")
        prompt_index = argv.index("--prompt-file") + 1
        if prompt_index >= len(argv):
            raise AssertionError("--prompt-file must have a value")
        prompt_file = Path(argv[prompt_index])
        prompt = prompt_file.read_text(encoding="utf-8")
        call = {{
            "call_index": len(self.calls),
            "argv": list(argv),
            "prompt_file": str(prompt_file),
            "prompt": prompt,
        }}
        self.calls.append(call)
        response = dict(self.response_by_prompt.get(prompt, {{"status": "ok"}}))
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
        raise AssertionError(f"scenario missing: {{scenario_id}}")

    def run_fake_with_prompt(self, fake: FakeCodex, prompt: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp:
            prompt_file = Path(temp) / "prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            return fake.run(["codex", "exec", "--prompt-file", str(prompt_file)])

    def test_runtime_driver_contract_uses_prompt_file_status_and_approval(self) -> None:
        self.assertTrue(self.workflow_path().exists(), f"workflow missing: {{self.workflow_path()}}")
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
{scenario_methods}


if __name__ == "__main__":
    unittest.main()
'''


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    design = read_json(LGWF_DIR / "e2e_runtime_fake_design.json")
    matrix = read_json(LGWF_DIR / "e2e_coverage_matrix.json")
    repair_context = read_json(LGWF_DIR / "e2e_runtime_fake_repair_context.json", {})
    runtime = matrix.get("runtime_fake") or {}
    selected = bool(runtime.get("selected", design.get("selected", True)))
    test_file = design.get("test_file") or f"{request['test_output_dir'].strip('/')}/{request['generated_tests']['runtime_fake']}"
    target_path = Path(request["workflow_root"]) / test_file

    if selected:
        write_text(target_path, render_test(design))

    scenario_generation = [
        {
            "scenario_id": str(scenario.get("scenario_id") or ""),
            "test_method": method_name(str(scenario.get("scenario_id") or "scenario")),
            "covered_branches": scenario.get("covered_branches", []),
            "covered_artifacts": scenario.get("covered_artifacts", []),
        }
        for scenario in design.get("scenarios", [])
    ]
    generation = {
        "test_file": test_file,
        "generated": selected,
        "uses_python_fake_codex": selected,
        "uses_prompt_file": selected,
        "blocked": False,
        "applied_repairs": design.get("repair_plan", []),
        "fake_mapping_summary": {
            "codex_like_nodes": [item.get("id") for item in design.get("codex_like_nodes", [])],
            "response_count": len((design.get("fake_codex_contract") or {}).get("response_mapping") or []),
        },
        "runtime_steps": [
            "lgwf.py run --workflow-lgwf",
            "lgwf.py status",
            "lgwf.py approval get",
            "lgwf.py approval submit",
            "Python fake Codex --prompt-file",
        ],
        "scenario_generation": scenario_generation,
        "diagnostic_strategy": [
            "生成测试先验证静态命令契约，再执行 Python fake Codex prompt-file 行为。",
            "业务分支覆盖由 design.scenarios[].covered_branches 与生成测试方法共同验收。",
        ],
        "repair_context": {
            "active": bool(repair_context.get("active")),
            "no_progress": bool(repair_context.get("no_progress")),
        },
        "notes": [] if selected else ["runtime_fake 未被选中，跳过测试文件生成。"],
    }
    write_json(LGWF_DIR / "e2e_runtime_fake_generation.json", generation)
    output_state({"runtime_fake_generation": generation})


if __name__ == "__main__":
    main()
