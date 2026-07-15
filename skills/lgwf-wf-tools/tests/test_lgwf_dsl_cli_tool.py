from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
LGWF = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


class LgwfDslCliToolTests(unittest.TestCase):
    def run_lgwf(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(LGWF), *args],
            cwd=FACADE_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )

    def test_tool_describe_exposes_lgwf_dsl_cli_schema(self) -> None:
        completed = self.run_lgwf("tool", "describe", "lgwf_dsl_cli")

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        payload = json.loads(completed.stdout)
        descriptor = payload["tool"]
        self.assertEqual(descriptor["name"], "lgwf_dsl_cli")
        self.assertEqual(
            descriptor["options_schema"]["properties"]["command"]["enum"],
            ["compile", "explain", "lint", "audit", "schema"],
        )

    def test_tool_schema_exposes_lgwf_dsl_cli_schemas(self) -> None:
        completed = self.run_lgwf("tool", "schema", "lgwf_dsl_cli")

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["tool"], "lgwf_dsl_cli")
        self.assertEqual(
            payload["options_schema"]["properties"]["command"]["enum"],
            ["compile", "explain", "lint", "audit", "schema"],
        )
        self.assertIn("properties", payload["output_schema"])

    def test_tool_run_audits_workflow_and_writes_result_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW demo;
ENTRY finish;

PY finish
  SCRIPT "finish.py"
  CONTRACT {
  };

FLOW finish;
""".lstrip(),
                encoding="utf-8",
            )
            (root / "finish.py").write_text("print('{}')\n", encoding="utf-8")
            options = {
                "command": "audit",
                "input": "workflow.lgwf",
                "result_output_path": ".lgwf/audit_result.json",
                "include_stdout": True,
                "fail_on_command_failure": False,
            }

            completed = self.run_lgwf(
                "tool",
                "run",
                "lgwf_dsl_cli",
                "--work-dir",
                str(root),
                "--options-json",
                json.dumps(options, ensure_ascii=False),
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            result = payload["result"]
            self.assertTrue(result["passed"], result)
            self.assertEqual(result["command"], "audit")
            artifact = root / ".lgwf" / "audit_result.json"
            self.assertTrue(artifact.is_file())
            artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertTrue(artifact_payload["passed"], artifact_payload)


if __name__ == "__main__":
    unittest.main()
