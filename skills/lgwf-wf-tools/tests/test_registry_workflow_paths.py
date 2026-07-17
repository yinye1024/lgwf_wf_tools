from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path, PurePosixPath


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = FACADE_ROOT / "registry.json"
SCRIPTS_ROOT = FACADE_ROOT / "scripts"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import list_workflows as list_workflows_module


PATH_PATTERNS = {
    "WORKFLOW": re.compile(r'\bWORKFLOW\s+"([^"]+)"'),
    "SCRIPT": re.compile(r'\bSCRIPT\s+"([^"]+)"'),
    "PROMPT_REF": re.compile(r'\bPROMPT_REF\s+"([^"]+)"'),
    "PROMPT": re.compile(r'\bPROMPT\s+"([^"]+)"'),
    "SPEC": re.compile(r'\bSPEC\s+"([^"]+)"'),
    "CONTEXT_WORKFLOW": re.compile(r'\bCONTEXT\s+workflow\s+(?:file|dir)\s+"([^"]+)"'),
}


def is_path_like_prompt(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.endswith((".md", ".txt", ".json"))


def validate_relative_path(value: str, label: str) -> None:
    path = PurePosixPath(value.replace("\\", "/"))
    if not value.strip():
        raise AssertionError(f"{label}: path is empty")
    if path.is_absolute() or ":" in value:
        raise AssertionError(f"{label}: path must be relative: {value}")
    if any(part == ".." for part in path.parts):
        raise AssertionError(f"{label}: path must not contain '..': {value}")


class RegistryWorkflowPathsTest(unittest.TestCase):
    def test_registry_declares_lgwf_and_tool_workflow_kinds(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        workflows = {workflow["id"]: workflow for workflow in registry["workflows"]}

        self.assertEqual("tool-workflow", workflows["self-improve"]["kind"])
        self.assertEqual("workflows/self-improve/AGENTS.md", workflows["self-improve"]["agents_md"])
        self.assertEqual("workflows/self-improve/scripts/self_improve.py", workflows["self-improve"]["entry"])
        self.assertNotIn("workflow_lgwf", workflows["self-improve"])
        self.assertNotIn("work_dir", workflows["self-improve"])

        self.assertEqual("tool-workflow", workflows["target-run"]["kind"])
        self.assertEqual("workflows/target-run/AGENTS.md", workflows["target-run"]["agents_md"])
        self.assertEqual("docs/target-run.md", workflows["target-run"]["entry"])
        self.assertNotIn("workflow_lgwf", workflows["target-run"])
        self.assertNotIn("work_dir", workflows["target-run"])

        self.assertEqual("tool-workflow", workflows["lgwf-guide"]["kind"])
        self.assertEqual("workflows/lgwf-guide/AGENTS.md", workflows["lgwf-guide"]["agents_md"])
        self.assertEqual("docs/lgwf-guide.md", workflows["lgwf-guide"]["entry"])
        self.assertNotIn("workflow_lgwf", workflows["lgwf-guide"])
        self.assertNotIn("work_dir", workflows["lgwf-guide"])

        self.assertEqual("tool-workflow", workflows["self-improve-seed"]["kind"])
        self.assertEqual("workflows/self-improve-seed/AGENTS.md", workflows["self-improve-seed"]["agents_md"])
        self.assertEqual("workflows/self-improve-seed/scripts/seed_self_improve.py", workflows["self-improve-seed"]["entry"])
        self.assertNotIn("workflow_lgwf", workflows["self-improve-seed"])
        self.assertNotIn("work_dir", workflows["self-improve-seed"])

        self.assertEqual("lgwf", workflows["skill-packaging"]["kind"])
        self.assertEqual("workflows/skill-packaging/AGENTS.md", workflows["skill-packaging"]["agents_md"])
        self.assertEqual("workflows/skill-packaging/wf/workflow.lgwf", workflows["skill-packaging"]["workflow_lgwf"])
        self.assertEqual("workflows/skill-packaging/ws", workflows["skill-packaging"]["work_dir"])
        self.assertNotIn("entry", workflows["skill-packaging"])

        for workflow_id, workflow in workflows.items():
            if workflow_id in {"self-improve", "target-run", "lgwf-guide", "self-improve-seed"}:
                continue
            self.assertEqual("lgwf", workflow["kind"], workflow_id)

    def test_registry_declared_paths_exist(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for workflow in registry["workflows"]:
            with self.subTest(workflow=workflow["id"]):
                fields = ("workflow_lgwf", "work_dir", "agents_md") if workflow["kind"] == "lgwf" else ("entry", "agents_md")
                for field in fields:
                    relative = workflow[field]
                    validate_relative_path(relative, f"{workflow['id']}.{field}")
                    self.assertTrue((FACADE_ROOT / relative).exists(), f"{workflow['id']}.{field}: {relative}")

    def test_skill_packaging_has_self_contained_operator_docs(self) -> None:
        workflow_root = FACADE_ROOT / "workflows" / "skill-packaging"
        readme = workflow_root / "README.md"
        agents = workflow_root / "AGENTS.md"
        contract = json.loads((workflow_root / "entry_contract.json").read_text(encoding="utf-8"))

        self.assertTrue(readme.is_file())
        readme_text = readme.read_text(encoding="utf-8")
        agents_text = agents.read_text(encoding="utf-8")
        self.assertIn("lgwf_workflow_package", readme_text)
        self.assertIn("LGWF workflow package", readme_text)
        self.assertIn("wf/workflow.lgwf", readme_text)
        self.assertIn("packaging_request", readme_text)
        self.assertIn("module-contract.md", agents_text)
        self.assertIn("README.md", agents_text)
        self.assertEqual(["packaging_request"], contract["input_schema"]["required"])
        request_schema = contract["input_schema"]["properties"]["packaging_request"]
        self.assertEqual(["source_skill", "output_parent"], request_schema["required"])
        self.assertIn("runtime_source", request_schema["properties"])
        self.assertIn("force", request_schema["properties"])

    def test_registry_entry_contracts_exist_and_match_workflows(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        allowed_input_modes = {"empty_then_approval", "input_json_required", "tool_args", "no_input"}
        allowed_auto_policies = {"allowed", "conditional", "forbidden", "not_applicable"}

        for workflow in registry["workflows"]:
            with self.subTest(workflow=workflow["id"]):
                contract_path = workflow.get("entry_contract")
                self.assertIsInstance(contract_path, str)
                validate_relative_path(contract_path, f"{workflow['id']}.entry_contract")
                contract = json.loads((FACADE_ROOT / contract_path).read_text(encoding="utf-8"))

                self.assertEqual(workflow["id"], contract["id"])
                self.assertEqual(workflow["kind"], contract["kind"])
                self.assertEqual(1, contract["version"])
                self.assertIn(contract["input_mode"], allowed_input_modes)
                self.assertIn(contract["auto_human_policy"], allowed_auto_policies)
                self.assertIsInstance(contract["state_boundary"], dict)

                input_schema = contract["input_schema"]
                self.assertEqual("object", input_schema["type"])
                self.assertIn("properties", input_schema)
                if contract["input_mode"] not in {"tool_args", "no_input"}:
                    self.assertIsInstance(input_schema.get("example"), dict)

                if workflow["kind"] == "lgwf":
                    self.assertEqual(workflow["workflow_lgwf"], contract["workflow_lgwf"])
                    self.assertEqual(workflow["work_dir"], contract["work_dir"])
                else:
                    self.assertIn("entry", contract)

    def test_list_workflows_includes_entry_contract_summary(self) -> None:
        result = list_workflows_module.list_workflows()
        by_id = {item["id"]: item for item in result["workflows"]}

        self.assertIn("entry_contract", by_id["wf-fix"])
        self.assertEqual("empty_then_approval", by_id["wf-fix"]["input_mode"])
        self.assertEqual("forbidden", by_id["wf-fix"]["auto_human_policy"])
        self.assertEqual([], by_id["wf-fix"]["required_fields"])

        self.assertEqual("input_json_required", by_id["wf-prompt-fix"]["input_mode"])
        self.assertEqual("conditional", by_id["wf-prompt-fix"]["auto_human_policy"])
        self.assertIn("prompt_fix_target", by_id["wf-prompt-fix"]["required_fields"])

        self.assertEqual("input_json_required", by_id["e2e-test-generator"]["input_mode"])
        self.assertEqual("conditional", by_id["e2e-test-generator"]["auto_human_policy"])
        self.assertEqual(["workflow_lgwf"], by_id["e2e-test-generator"]["required_fields"])

    def test_registered_lgwf_workflows_have_self_improve_modules(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        required = [
            "self-improve/manifest.json",
            "self-improve/scripts/self_improve.py",
            "self-improve/scripts/check_self_improve.py",
        ]
        missing: list[str] = []
        forbidden_text: list[str] = []
        for workflow in registry["workflows"]:
            if workflow["kind"] != "lgwf":
                continue
            if workflow["id"] == "wf-create-fast":
                continue
            workflow_root = (FACADE_ROOT / workflow["agents_md"]).parent
            for relative in required:
                if not (workflow_root / relative).is_file():
                    missing.append(f"{workflow['id']}: {relative}")
            scripts_root = workflow_root / "self-improve" / "scripts"
            if scripts_root.is_dir():
                for script in scripts_root.glob("*.py"):
                    text = script.read_text(encoding="utf-8")
                    if "lgwf-wf-tools" in text or "workflows/self-improve" in text:
                        forbidden_text.append(f"{workflow['id']}: {script.relative_to(workflow_root).as_posix()}")

        self.assertEqual([], missing)
        self.assertEqual([], forbidden_text)

    def test_workflow_lgwf_references_exist_and_are_relative(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        missing: list[str] = []
        invalid: list[str] = []
        for workflow in registry["workflows"]:
            if workflow["kind"] != "lgwf":
                continue
            package_root = (FACADE_ROOT / workflow["workflow_lgwf"]).parent
            for workflow_file in package_root.rglob("workflow.lgwf"):
                text = workflow_file.read_text(encoding="utf-8")
                for kind, pattern in PATH_PATTERNS.items():
                    for match in pattern.finditer(text):
                        value = match.group(1)
                        if kind == "PROMPT" and not is_path_like_prompt(value):
                            continue
                        try:
                            validate_relative_path(value, f"{workflow['id']}:{workflow_file}:{kind}")
                        except AssertionError as exc:
                            invalid.append(str(exc))
                            continue
                        target = workflow_file.parent / value
                        if not target.exists() and value.replace("\\", "/").startswith("workflows/"):
                            target = FACADE_ROOT / value
                        if not target.exists():
                            missing.append(
                                f"{workflow['id']}: {workflow_file.relative_to(package_root).as_posix()} "
                                f"{kind} {value}"
                            )
        self.assertEqual([], invalid)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
