from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import lgwf.runtime as runtime_module
import lgwf_client.main_agent.approvals as main_agent_approvals_module
import lgwf_client.main_agent.status as main_agent_status_module
import lgwf_dsl.auditor as auditor_module
import lgwf_dsl.compiler as compiler_module


class RunWorkflowDslTest(unittest.TestCase):
    def test_run_workflow_compiles_to_flow_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_success_child(root / "child")
            parent = _write_parent(root)
            workflow = _compile(parent, root)

        node = workflow["nodes"][0]
        self.assertEqual(node["capability"], "flow.run_workflow")
        self.assertEqual(node["config"]["workflow_lgwf"], "child/workflow.lgwf")
        self.assertEqual(node["config"]["work_dir"], "child_ws")
        self.assertEqual(node["config"]["input_path"], "pipeline.child_input")
        self.assertEqual(node["config"]["result_path"], "pipeline.child_result")

    def test_run_workflow_audit_fails_for_missing_child(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = root / "parent" / "workflow.lgwf"
            parent.parent.mkdir()
            parent.write_text(
                """
WORKFLOW parent;
ENTRY child;

RUN_WORKFLOW child
  WORKFLOW "missing/workflow.lgwf"
  WORK_DIR "child_ws"
  INPUT state.pipeline.child_input
  RESULT state.pipeline.child_result;
""".strip()
                + "\n",
                encoding="utf-8",
            )
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                payload, exit_code = auditor_module.WorkflowAuditor().audit(parent)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(exit_code, 1)
        diagnostics = payload["diagnostics"]
        self.assertTrue(any("RUN_WORKFLOW WORKFLOW" in item["message"] for item in diagnostics))


class RunWorkflowRuntimeTest(unittest.TestCase):
    def test_run_workflow_writes_child_result_from_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_success_child(root / "child")
            parent = _write_parent(root)
            workflow = _compile(parent, root)
            parent_ws = root / "parent_ws"
            parent_ws.mkdir()
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                final_state = runtime_module.invoke_dsl(
                    workflow,
                    {"pipeline": {"child_input": {"message": "hello"}}},
                    workflow_root=parent.parent,
                    workspace_root=parent_ws,
                    record=True,
                )
            finally:
                os.chdir(previous_cwd)
            child_record_exists = (parent_ws / ".lgwf" / "child-runs" / "child.json").is_file()
            child_runs_exists = (root / "child_ws" / ".lgwf" / "runs").is_dir()

        child_result = final_state["pipeline"]["child_result"]
        self.assertEqual(child_result["status"], "completed")
        self.assertEqual(child_result["final_state"]["child"]["done"]["ok"], True)
        self.assertNotEqual(child_result["final_state"]["child"]["done"]["pid"], os.getpid())
        self.assertIn("run_id", child_result)
        self.assertTrue(child_record_exists)
        self.assertTrue(child_runs_exists)

    def test_run_workflow_failure_records_child_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_failing_child(root / "child")
            parent = _write_parent(root)
            workflow = _compile(parent, root)
            parent_ws = root / "parent_ws"
            parent_ws.mkdir()
            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with self.assertRaises(RuntimeError):
                    runtime_module.invoke_dsl(
                        workflow,
                        {"pipeline": {"child_input": {"message": "hello"}}},
                        workflow_root=parent.parent,
                        workspace_root=parent_ws,
                        record=True,
                    )
            finally:
                os.chdir(previous_cwd)

            record = json.loads((parent_ws / ".lgwf" / "child-runs" / "child.json").read_text(encoding="utf-8"))

        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["returncode"], 2)
        self.assertIn("child workflow failed", record["failure"]["message"])
        self.assertIn("stderr", record)

    def test_child_approval_is_visible_and_submittable_from_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_approval_child(root / "child")
            parent = _write_parent(root)
            workflow = _compile(parent, root)
            parent_ws = root / "parent_ws"
            parent_ws.mkdir()
            workflow_json = parent_ws / "workflow.json"
            workflow_json.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
            input_json = json.dumps({"pipeline": {"child_input": {"child_request": {"ok": True}}}})
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "lgwf_client.cli",
                    "--workflow-json",
                    str(workflow_json),
                    "--work-dir",
                    str(parent_ws),
                    "--input-json",
                    input_json,
                ],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                pending_action = _wait_for_child_approval(parent_ws, process)
                self.assertEqual(pending_action["type"], "child_human_approval")
                self.assertEqual(pending_action["child_node"], "child")
                main_agent_approvals_module.submit_main_agent_approval(
                    parent_ws,
                    pending_action["request_id"],
                    decision="approve",
                    value={"approved": True},
                    comment="test approval",
                )
                stdout, stderr = process.communicate(timeout=20)
            finally:
                if process.poll() is None:
                    process.kill()

        self.assertEqual(process.returncode, 0, stderr)
        final_state = json.loads(stdout)
        child_result = final_state["pipeline"]["child_result"]
        self.assertEqual(child_result["status"], "completed")
        self.assertEqual(child_result["final_state"]["child_approved"]["approved"], True)


def _compile(parent: Path, cwd: Path) -> dict:
    previous_cwd = Path.cwd()
    try:
        os.chdir(cwd)
        return compiler_module.WorkflowDslCompiler().compile_text(
            parent.read_text(encoding="utf-8"),
            source_name=str(parent),
            package_root=parent.parent,
        )
    finally:
        os.chdir(previous_cwd)


def _write_parent(root: Path) -> Path:
    parent = root / "parent" / "workflow.lgwf"
    parent.parent.mkdir()
    parent.write_text(
        """
WORKFLOW parent;
ENTRY child;

RUN_WORKFLOW child
  WORKFLOW "child/workflow.lgwf"
  WORK_DIR "child_ws"
  INPUT state.pipeline.child_input
  RESULT state.pipeline.child_result;
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return parent


def _write_success_child(root: Path) -> None:
    (root / "scripts").mkdir(parents=True)
    (root / "workflow.lgwf").write_text(
        """
WORKFLOW child;
ENTRY done;

PY done
  SCRIPT "scripts/done.py"
  RESULT state.child.done
  UPDATES_STATE;
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "scripts" / "done.py").write_text(
        "import json\nimport os\nprint(json.dumps({'child.done': {'ok': True, 'pid': os.getpid()}}))\n",
        encoding="utf-8",
    )


def _write_failing_child(root: Path) -> None:
    (root / "scripts").mkdir(parents=True)
    (root / "workflow.lgwf").write_text(
        """
WORKFLOW child;
ENTRY fail;

PY fail
  SCRIPT "scripts/fail.py"
  RESULT state.child.fail;
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "scripts" / "fail.py").write_text(
        "raise RuntimeError('planned child failure')\n",
        encoding="utf-8",
    )


def _write_approval_child(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "workflow.lgwf").write_text(
        """
WORKFLOW child_approval;
ENTRY confirm;

APPROVAL confirm
  PROMPT "confirm child"
  READ state.child_request
  WRITE state.child_approved
  RESULT state.child_approval_result;
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _wait_for_child_approval(parent_ws: Path, process: subprocess.Popen) -> dict:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"process exited before approval\nstdout={stdout}\nstderr={stderr}")
        status = main_agent_status_module.get_main_agent_status(parent_ws, pid=process.pid)
        pending_action = status.get("pending_action")
        if isinstance(pending_action, dict) and pending_action.get("type") == "child_human_approval":
            return pending_action
        time.sleep(0.2)
    raise AssertionError("timed out waiting for child approval")


if __name__ == "__main__":
    unittest.main()
