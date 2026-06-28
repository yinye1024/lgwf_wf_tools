from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lgwf_dsl.auditor import WorkflowAuditor


def audit_package(files: dict[str, str], entry: str = "workflow.lgwf") -> dict:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        payload, _exit_code = WorkflowAuditor().audit(root / entry)
        return payload


PROMPT = "# Role\nDo work.\n"


class ArtifactContractAuditTest(unittest.TestCase):
    def test_missing_workspace_artifact_producer_fails_audit(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY apply_fix;

CODEX apply_fix
  PROMPT "prompt.md"
  CONTEXT workspace file ".lgwf/repair_plan.json";
""",
                "prompt.md": PROMPT,
            }
        )

        self.assertFalse(payload["passed"])
        codes = {item["code"] for item in payload["diagnostics"]}
        self.assertIn("LGWF_ARTIFACT_CONTRACT_MISSING", codes)

    def test_output_json_producer_satisfies_react_consumer(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY repair;

REACT repair MAX 1
  REASON CODEX
    PROMPT "reason.md"
    OUTPUT_JSON ".lgwf/repair_plan.json" AS_FILE
  ACT CODEX
    PROMPT "act.md"
    CONTEXT workspace file ".lgwf/repair_plan.json"
  OBSERVE CODEX
    PROMPT "observe.md"
    CONTEXT workspace file ".lgwf/repair_plan.json"
  DECIDE PY
    SCRIPT "decide.py";
""",
                "reason.md": PROMPT,
                "act.md": PROMPT,
                "observe.md": PROMPT,
                "decide.py": "print('{}')\n",
            }
        )

        self.assertTrue(payload["passed"], json.dumps(payload["diagnostics"], ensure_ascii=False))

    def test_approval_persist_satisfies_consumer(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY collect;

APPROVAL collect
  PROMPT "确认"
  READ state.input
  WRITE state.request
  PERSIST ".lgwf/request.json";

CODEX use_request
  PROMPT "prompt.md"
  CONTEXT workspace file ".lgwf/request.json";

FLOW collect THEN use_request;
""",
                "prompt.md": PROMPT,
            }
        )

        self.assertTrue(payload["passed"], json.dumps(payload["diagnostics"], ensure_ascii=False))

    def test_artifact_contracts_bootstrap_input_satisfies_consumer(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY inspect;

CODEX inspect
  PROMPT "prompt.md"
  CONTEXT workspace file ".lgwf/request.json";
""",
                "prompt.md": PROMPT,
                "artifact_contracts.json": json.dumps({"bootstrap_inputs": [".lgwf/request.json"]}),
            }
        )

        self.assertTrue(payload["passed"], json.dumps(payload["diagnostics"], ensure_ascii=False))

    def test_artifact_contracts_script_writes_satisfies_consumer(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY prepare;

PY prepare
  SCRIPT "prepare.py";

CODEX inspect
  PROMPT "prompt.md"
  CONTEXT workspace file ".lgwf/prepared.json";

FLOW prepare THEN inspect;
""",
                "prompt.md": PROMPT,
                "prepare.py": "print('{}')\n",
                "artifact_contracts.json": json.dumps(
                    {"script_writes": {"prepare": [".lgwf/prepared.json"]}}
                ),
            }
        )

        self.assertTrue(payload["passed"], json.dumps(payload["diagnostics"], ensure_ascii=False))

    def test_artifact_contracts_script_writes_rejects_unknown_node(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY prepare;

PY prepare
  SCRIPT "prepare.py";

CODEX inspect
  PROMPT "prompt.md"
  CONTEXT workspace file ".lgwf/prepared.json";

FLOW prepare THEN inspect;
""",
                "prompt.md": PROMPT,
                "prepare.py": "print('{}')\n",
                "artifact_contracts.json": json.dumps(
                    {"script_writes": {"missing_prepare": [".lgwf/prepared.json"]}}
                ),
            }
        )

        self.assertFalse(payload["passed"])
        diagnostics = payload["diagnostics"]
        self.assertIn("LGWF_ARTIFACT_CONTRACT_INVALID", {item["code"] for item in diagnostics})
        self.assertTrue(
            any("unknown PY node" in item["message"] for item in diagnostics),
            json.dumps(diagnostics, ensure_ascii=False),
        )

    def test_output_file_producer_satisfies_non_json_consumer(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY reason;

CODEX reason
  PROMPT "reason.md"
  OUTPUT_FILE ".lgwf/reason.md";

CODEX act
  PROMPT "act.md"
  CONTEXT workspace file ".lgwf/reason.md";

FLOW reason THEN act;
""",
                "reason.md": PROMPT,
                "act.md": PROMPT,
            }
        )

        self.assertTrue(payload["passed"], json.dumps(payload["diagnostics"], ensure_ascii=False))

    def test_output_file_rejects_json_path(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY reason;

CODEX reason
  PROMPT "reason.md"
  OUTPUT_FILE ".lgwf/reason.json";
""",
                "reason.md": PROMPT,
            }
        )

        self.assertFalse(payload["passed"])
        self.assertTrue(
            any("OUTPUT_FILE" in item["message"] and "OUTPUT_JSON" in item["message"] for item in payload["diagnostics"]),
            json.dumps(payload["diagnostics"], ensure_ascii=False),
        )

    def test_non_lgwf_workspace_file_is_not_checked(self) -> None:
        payload = audit_package(
            {
                "workflow.lgwf": """
WORKFLOW demo;
ENTRY inspect;

CODEX inspect
  PROMPT "prompt.md"
  CONTEXT workspace file "reports/input.json";
""",
                "prompt.md": PROMPT,
            }
        )

        self.assertTrue(payload["passed"], json.dumps(payload["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
