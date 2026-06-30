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
    def test_registry_declared_paths_exist(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for workflow in registry["workflows"]:
            with self.subTest(workflow=workflow["id"]):
                for field in ("workflow_lgwf", "work_dir", "agents_md"):
                    relative = workflow[field]
                    validate_relative_path(relative, f"{workflow['id']}.{field}")
                    self.assertTrue((FACADE_ROOT / relative).exists(), f"{workflow['id']}.{field}: {relative}")

    def test_workflow_lgwf_references_exist_and_are_relative(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        missing: list[str] = []
        invalid: list[str] = []
        for workflow in registry["workflows"]:
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
