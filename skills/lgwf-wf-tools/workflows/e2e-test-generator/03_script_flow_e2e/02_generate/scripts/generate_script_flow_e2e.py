from __future__ import annotations

from pathlib import Path
import json
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json, write_text


def py_literal(value: Any) -> str:
    return repr(value)


def render_test(design: dict[str, Any]) -> str:
    return f'''from __future__ import annotations

import py_compile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILES = {py_literal(design.get("workflow_files", []))}
SCRIPT_ENTRIES = {py_literal(design.get("script_entries", []))}
ROUTE_ENTRIES = {py_literal(design.get("route_entries", []))}
APPROVAL_PERSIST_ENTRIES = {py_literal(design.get("approval_persist_entries", []))}
FORBIDDEN_PATTERNS = ["lgwf.py " + "run", "--workflow-" + "lgwf", "co" + "dex"]


class GeneratedScriptFlowE2ETest(unittest.TestCase):
    def workflow_text(self, relative: str) -> str:
        path = ROOT / relative
        self.assertTrue(path.exists(), f"workflow file missing: {{relative}}")
        return path.read_text(encoding="utf-8")

    def test_case_script_contracts_compile(self) -> None:
        self.assertTrue(SCRIPT_ENTRIES, "script contracts should not be empty")
        for entry in SCRIPT_ENTRIES:
            with self.subTest(script=entry["resolved_path"]):
                script_path = ROOT / entry["resolved_path"]
                self.assertTrue(script_path.exists(), f"script missing: {{entry['resolved_path']}}")
                py_compile.compile(str(script_path), doraise=True)

    def test_case_routes_declared(self) -> None:
        for route in ROUTE_ENTRIES:
            with self.subTest(route=route):
                text = self.workflow_text(route["workflow"])
                expected = f'WHEN "{{route["value"]}}" THEN {{route["target"]}}'
                self.assertIn(expected, text)

    def test_case_approval_persist_declared(self) -> None:
        for entry in APPROVAL_PERSIST_ENTRIES:
            with self.subTest(artifact=entry):
                text = self.workflow_text(entry["workflow"])
                self.assertIn(f'PERSIST "{{entry["artifact"]}}"', text)

    def test_case_no_runtime_or_model_launch_guard(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)


if __name__ == "__main__":
    unittest.main()
'''


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    design = read_json(LGWF_DIR / "e2e_script_flow_design.json")
    matrix = read_json(LGWF_DIR / "e2e_coverage_matrix.json")
    selected = bool((matrix.get("script_flow") or {}).get("selected", design.get("selected", True)))
    test_file = design.get("test_file") or f"{request['test_output_dir'].strip('/')}/{request['generated_tests']['script_flow']}"
    target_path = Path(request["workflow_root"]) / test_file

    if selected:
        write_text(target_path, render_test(design))

    coverage = [
        {"coverage_ref": claim["coverage_ref"], "case_ids": claim["case_ids"]}
        for claim in design.get("coverage_claims", [])
    ]
    generation = {
        "test_file": test_file,
        "generated": selected,
        "coverage": coverage,
        "case_mappings": [
            {
                "case_id": case["case_id"],
                "test_method": f"test_{case['case_id']}",
                "coverage_refs": case.get("coverage_refs", []),
                "implemented_assertions": [
                    *case.get("route_assertions", []),
                    *case.get("artifact_assertions", []),
                    *case.get("forbidden_assertions", []),
                ],
            }
            for case in design.get("cases", [])
        ],
        "guard_mechanisms": [
            {
                "guard_type": "static_source_guard",
                "description": "生成的脚本级测试只读取文件、编译脚本并检查声明，不启动 runtime 或真实模型。",
            }
        ],
        "notes": [] if selected else ["script_flow 未被选中，跳过测试文件生成。"],
    }
    write_json(LGWF_DIR / "e2e_script_flow_generation.json", generation)
    output_state({"script_flow_generation": generation})


if __name__ == "__main__":
    main()
