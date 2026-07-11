from __future__ import annotations

import json
import re
import unittest
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


FACADE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_ROOT = FACADE_ROOT / "workflows"
REGISTRY = FACADE_ROOT / "registry.json"
EXCLUDED_SOURCE_PARTS = {".local", "tests", "ws", "__pycache__"}
CONTRACT_REQUIRED_KINDS = {
    "ACT CODEX",
    "AGENT",
    "AGENT_LOOP",
    "APPROVAL",
    "CHOICE",
    "CODEX",
    "DECIDE PY",
    "DIAGNOSE CODEX",
    "OBSERVE PY",
    "OBSERVE WORKFLOW",
    "OBSERVE CODEX",
    "PLAN CODEX",
    "PY",
    "REASON CODEX",
    "REVIEW",
    "RUN_WORKFLOW",
    "VERIFY PY",
    "VERIFY WORKFLOW",
}


NODE_RE = re.compile(
    r"^\s*(?:(REASON|ACT|OBSERVE|VERIFY|DECIDE|DIAGNOSE|PLAN)\s+)?"
    r"(STEP|PY|APPROVAL|REVIEW|HANDOFF|AGENT|AGENT_LOOP|CODEX|CHOICE|RUN_WORKFLOW|WORKFLOW)"
    r"(?:\s+([A-Za-z0-9_-]+))?\b"
)
CONTRACT_RE = re.compile(r"\bCONTRACT\s*\{")
CONTRACT_ENTRY_RE = re.compile(r"\b(READ|WRITE)\s+([^;]+);")
CONTEXT_RE = re.compile(r'\bCONTEXT\s+(workspace|workflow)\s+(file|dir)\s+"([^"]+)"')
OUTPUT_RE = re.compile(r'\b(OUTPUT_JSON|OUTPUT_FILE|PERSIST)\s+"([^"]+)"')
INPUT_STATE_RE = re.compile(r"\bINPUT\s+(state\.[A-Za-z0-9_.]+)")
READ_STATE_RE = re.compile(r"\bREAD\s+(state\.[A-Za-z0-9_.]+)")
WRITE_STATE_RE = re.compile(r"\bWRITE\s+(state\.[A-Za-z0-9_.]+)")
WORKFLOW_REF_RE = re.compile(r'\bWORKFLOW\s+"([^"]+)"')
WORK_DIR_RE = re.compile(r'\bWORK_DIR\s+"([^"]+)"')


@dataclass
class NodeContract:
    workflow_file: Path
    kind: str
    name: str
    line: int
    lines: list[str] = field(default_factory=list)
    has_contract: bool = False
    contract_entries: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        relative = self.workflow_file.relative_to(FACADE_ROOT).as_posix()
        return f"{relative}:{self.line} {self.kind} {self.name}"


def source_lgwf_files() -> list[Path]:
    return sorted(
        path
        for path in WORKFLOWS_ROOT.rglob("*.lgwf")
        if path.is_file() and not any(part in EXCLUDED_SOURCE_PARTS for part in path.parts)
    )


def validate_contract_path(path_value: str, *, label: str) -> None:
    path = PurePosixPath(path_value.replace("\\", "/"))
    if not path_value.strip():
        raise AssertionError(f"{label}: path is empty")
    if path.is_absolute() or ":" in path_value:
        raise AssertionError(f"{label}: path must be package-relative: {path_value}")
    if any(part == ".." for part in path.parts):
        raise AssertionError(f"{label}: path must not contain '..': {path_value}")


def parse_nodes(workflow_file: Path) -> list[NodeContract]:
    nodes: list[NodeContract] = []
    current: NodeContract | None = None
    contract_depth = 0
    in_contract = False
    for line_number, line in enumerate(workflow_file.read_text(encoding="utf-8").splitlines(), start=1):
        match = NODE_RE.match(line)
        if match:
            phase, kind, name = match.groups()
            full_kind = f"{phase} {kind}" if phase else kind
            if full_kind != "WORKFLOW":
                if current is not None:
                    nodes.append(current)
                current = NodeContract(
                    workflow_file=workflow_file,
                    kind=full_kind,
                    name=name or f"{full_kind.lower().replace(' ', '_')}_{line_number}",
                    line=line_number,
                )
                in_contract = False
                contract_depth = 0
        if current is None:
            continue
        current.lines.append(line)
        if CONTRACT_RE.search(line):
            current.has_contract = True
            in_contract = True
            contract_depth = line.count("{") - line.count("}")
            current.contract_entries.extend(f"{action} {target.strip()}" for action, target in CONTRACT_ENTRY_RE.findall(line))
            if contract_depth <= 0:
                in_contract = False
        elif in_contract:
            current.contract_entries.extend(f"{action} {target.strip()}" for action, target in CONTRACT_ENTRY_RE.findall(line))
            contract_depth += line.count("{") - line.count("}")
            if contract_depth <= 0:
                in_contract = False
    if current is not None:
        nodes.append(current)
    return nodes


def contract_has(entries: list[str], expected: str) -> bool:
    return expected in entries


class WorkflowNodeContractTests(unittest.TestCase):
    def test_source_scan_excludes_runtime_and_test_workflow_copies(self) -> None:
        files = source_lgwf_files()
        self.assertGreaterEqual(len(files), 60)
        for path in files:
            relative = path.relative_to(WORKFLOWS_ROOT).parts
            self.assertFalse(any(part in EXCLUDED_SOURCE_PARTS for part in relative), path.as_posix())

    def test_contract_relevant_nodes_have_explicit_contract_blocks(self) -> None:
        missing: list[str] = []
        for workflow_file in source_lgwf_files():
            for node in parse_nodes(workflow_file):
                if node.kind in CONTRACT_REQUIRED_KINDS and not node.has_contract:
                    missing.append(node.label)
        self.assertEqual([], missing)

    def test_declared_file_io_is_reflected_in_same_node_contract(self) -> None:
        failures: list[str] = []
        for workflow_file in source_lgwf_files():
            for node in parse_nodes(workflow_file):
                text = "\n".join(node.lines)
                for context_root, context_kind, context_path in CONTEXT_RE.findall(text):
                    expected = f'READ {context_root} {context_kind} "{context_path}"'
                    if not contract_has(node.contract_entries, expected):
                        failures.append(f"{node.label}: missing {expected}")
                for _, output_path in OUTPUT_RE.findall(text):
                    expected = f'WRITE workspace file "{output_path}"'
                    if not contract_has(node.contract_entries, expected):
                        failures.append(f"{node.label}: missing {expected}")
                if node.kind == "RUN_WORKFLOW":
                    for input_state in INPUT_STATE_RE.findall(text):
                        expected = f"READ {input_state}"
                        if not contract_has(node.contract_entries, expected):
                            failures.append(f"{node.label}: missing {expected}")
                    for workflow_ref in WORKFLOW_REF_RE.findall(text):
                        expected = f'READ workspace file "{workflow_ref}"'
                        if not contract_has(node.contract_entries, expected):
                            failures.append(f"{node.label}: missing {expected}")
                    for work_dir in WORK_DIR_RE.findall(text):
                        expected = f'WRITE workspace dir "{work_dir}"'
                        if not contract_has(node.contract_entries, expected):
                            failures.append(f"{node.label}: missing {expected}")
        self.assertEqual([], failures)

    def test_contract_resource_paths_are_relative_and_outputs_are_not_self_reads(self) -> None:
        failures: list[str] = []
        for workflow_file in source_lgwf_files():
            for node in parse_nodes(workflow_file):
                declared_outputs = {path for _, path in OUTPUT_RE.findall("\n".join(node.lines))}
                for entry in node.contract_entries:
                    resource_match = re.match(r'(READ|WRITE)\s+(?:workspace|workflow)\s+(?:file|dir)\s+"([^"]+)"', entry)
                    if not resource_match:
                        continue
                    action, path_value = resource_match.groups()
                    try:
                        validate_contract_path(path_value, label=node.label)
                    except AssertionError as exc:
                        failures.append(str(exc))
                    if action == "READ" and path_value in declared_outputs:
                        failures.append(f"{node.label}: output {path_value} must not be a same-node READ")
        self.assertEqual([], failures)

    def test_wf_create_contract_file_entries_are_concrete_paths(self) -> None:
        failures: list[str] = []
        for workflow_file in source_lgwf_files_for_package(WORKFLOWS_ROOT / "wf-create"):
            for node in parse_nodes(workflow_file):
                for entry in node.contract_entries:
                    resource_match = re.match(r'(READ|WRITE)\s+workspace\s+file\s+"([^"]+)"', entry)
                    if not resource_match:
                        continue
                    action, path_value = resource_match.groups()
                    if "*" in path_value or "?" in path_value or "|" in path_value:
                        failures.append(f"{node.label}: {action} workspace file must be concrete: {path_value}")
        self.assertEqual([], failures)

    def test_workflow_packages_have_artifact_contract_files(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        missing: list[str] = []
        invalid: list[str] = []
        for item in registry["workflows"]:
            package_root = FACADE_ROOT / "workflows" / item["id"]
            if not source_lgwf_files_for_package(package_root):
                continue
            contracts = [
                path
                for path in package_root.rglob("artifact_contracts.json")
                if path.is_file() and not any(part in EXCLUDED_SOURCE_PARTS for part in path.parts)
            ]
            if not contracts:
                missing.append(item["id"])
                continue
            for contract in contracts:
                payload = json.loads(contract.read_text(encoding="utf-8"))
                if "bootstrap_inputs" not in payload or "script_writes" not in payload:
                    invalid.append(contract.relative_to(FACADE_ROOT).as_posix())
        self.assertEqual([], missing)
        self.assertEqual([], invalid)


def source_lgwf_files_for_package(package_root: Path) -> list[Path]:
    return [
        path
        for path in package_root.rglob("*.lgwf")
        if path.is_file() and not any(part in EXCLUDED_SOURCE_PARTS for part in path.parts)
    ]


if __name__ == "__main__":
    unittest.main()
