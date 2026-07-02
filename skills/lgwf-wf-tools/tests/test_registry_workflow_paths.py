from __future__ import annotations

import json
import re
import unittest
from pathlib import Path, PurePosixPath


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = FACADE_ROOT / "registry.json"


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

        for workflow_id, workflow in workflows.items():
            if workflow_id in {"self-improve", "target-run"}:
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
                        if not target.exists():
                            missing.append(
                                f"{workflow['id']}: {workflow_file.relative_to(package_root).as_posix()} "
                                f"{kind} {value}"
                            )
        self.assertEqual([], invalid)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
