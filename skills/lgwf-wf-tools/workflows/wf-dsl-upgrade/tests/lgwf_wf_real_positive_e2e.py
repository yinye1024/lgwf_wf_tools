from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[4]
SOURCE_WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
SOURCE_CONFIRM_WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "05_confirm_upgrade_plan" / "workflow.lgwf"
LGWF_PY = (
    PACKAGE_ROOT.parent.parent
    / "vendor"
    / "lgwf-client-assist"
    / "scripts"
    / "lgwf.py"
)
STATUS_POLL_INTERVAL_SECONDS = 1
STATUS_TIMEOUT_SECONDS = 180
PHASE_CHANGE_TIMEOUT_SECONDS = 20


def run_lgwf(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(LGWF_PY), *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def parse_json_object(text: str, required_keys: set[str] | None = None) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw.startswith("{"):
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and (required_keys is None or required_keys.issubset(payload)):
            matches.append(payload)
    if matches:
        return matches[-1]
    expected = f" with keys {sorted(required_keys)}" if required_keys else ""
    raise AssertionError(f"stdout 未包含 JSON object{expected}:\n{text}")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class RealPositiveHarness:
    def __init__(self) -> None:
        suffix = time.strftime("%Y%m%d-%H%M%S")
        self.temp_root = Path(tempfile.mkdtemp(prefix=f"wf-dsl-upgrade-real-positive-{suffix}-"))
        self.fixture_targets = self.temp_root / "fixture_targets"
        self.runtime_work = self.temp_root / "runtime_work"
        self.artifacts_dir = self.temp_root / "artifacts"
        self.input_json = self.temp_root / "input.json"
        self.audit_stdout = self.artifacts_dir / "audit.stdout.txt"
        self.audit_stderr = self.artifacts_dir / "audit.stderr.txt"
        self.audit_command = self.artifacts_dir / "audit.command.txt"
        self.run_log = self.runtime_work / ".lgwf" / "real_positive_runtime.log"
        self.command_trace = self.artifacts_dir / "command_trace.jsonl"
        self.status_trace = self.artifacts_dir / "status_trace.jsonl"
        self.approval_trace = self.artifacts_dir / "approval_trace.jsonl"
        self.fixture_hashes_before: dict[str, str] = {}
        self.fixture_hashes_after: dict[str, str] = {}
        self.approval_events: list[dict[str, Any]] = []
        self.session_id = ""
        self.pid: int | None = None

    @property
    def root_fixture_workflow(self) -> Path:
        return self.fixture_targets / "workflow.lgwf"

    @property
    def confirm_fixture_workflow(self) -> Path:
        return self.fixture_targets / "05_confirm_upgrade_plan" / "workflow.lgwf"

    def prepare(self) -> None:
        self.fixture_targets.mkdir(parents=True, exist_ok=True)
        self.runtime_work.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.confirm_fixture_workflow.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE_WORKFLOW_LGWF, self.root_fixture_workflow)
        shutil.copy2(SOURCE_CONFIRM_WORKFLOW_LGWF, self.confirm_fixture_workflow)

        self.fixture_hashes_before = {
            str(self.root_fixture_workflow): sha256_file(self.root_fixture_workflow),
            str(self.confirm_fixture_workflow): sha256_file(self.confirm_fixture_workflow),
        }
        self.write_input_json()

    def write_input_json(self) -> None:
        targets = [
            str(self.root_fixture_workflow),
            str(self.confirm_fixture_workflow),
        ]
        payload = {
            "dsl_upgrade_target": {
                "target_paths": targets,
                "mode": "apply",
                "allowed_dirs": [str(self.fixture_targets)],
            },
            "request": {
                "payload": {
                    "scope_mode": "registry",
                    "targets": targets,
                    "max_targets": 8,
                    "mode": "apply",
                }
            },
            "input": {
                "payload": {
                    "scope_mode": "registry",
                    "targets": targets,
                    "max_targets": 8,
                    "mode": "apply",
                }
            },
            "scope_mode": "registry",
            "targets": targets,
            "max_targets": 8,
            "mode": "apply",
        }
        write_json(self.input_json, payload)

    def record_command(self, args: list[str], completed: subprocess.CompletedProcess[str]) -> None:
        append_jsonl(
            self.command_trace,
            {
                "args": args,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )

    def run_cli(self, *args: str, timeout: int = 30, required_keys: set[str] | None = None) -> dict[str, Any]:
        command = list(args)
        completed = run_lgwf(command, timeout=timeout)
        self.record_command(command, completed)
        if completed.returncode != 0:
            raise AssertionError(
                f"命令失败: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return parse_json_object(completed.stdout, required_keys)

    def run_audit(self) -> None:
        args = ["audit", str(SOURCE_WORKFLOW_LGWF)]
        self.audit_command.write_text(f"python {LGWF_PY} {' '.join(args)}\n", encoding="utf-8")
        completed = run_lgwf(args, timeout=60)
        self.record_command(args, completed)
        self.audit_stdout.write_text(completed.stdout, encoding="utf-8")
        self.audit_stderr.write_text(completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            raise AssertionError(
                f"audit 失败: {SOURCE_WORKFLOW_LGWF}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )

    def start_runtime(self) -> None:
        inline_input = self.input_json.read_text(encoding="utf-8")
        payload = self.run_cli(
            "run",
            "--workflow-lgwf",
            str(SOURCE_WORKFLOW_LGWF),
            "--work-dir",
            str(self.runtime_work),
            "--input-json",
            inline_input,
            "--background",
            "--log-file",
            str(self.run_log),
            timeout=60,
            required_keys={"session_id"},
        )
        self.session_id = str(payload["session_id"])
        pid_value = payload.get("pid")
        if isinstance(pid_value, int):
            self.pid = pid_value
        elif isinstance(pid_value, str) and pid_value.isdigit():
            self.pid = int(pid_value)

    def stop_runtime(self) -> None:
        if self.pid is None:
            return
        completed = run_lgwf(["stop", "--pid", str(self.pid)], timeout=30)
        self.record_command(["stop", "--pid", str(self.pid)], completed)

    def status(self) -> dict[str, Any]:
        payload = self.run_cli(
            "status",
            "--work-dir",
            str(self.runtime_work),
            "--session-id",
            self.session_id,
            timeout=30,
        )
        append_jsonl(self.status_trace, payload)
        return payload

    def approval_get(self, request_id: str) -> dict[str, Any]:
        payload = self.run_cli(
            "approval",
            "get",
            "--work-dir",
            str(self.runtime_work),
            "--request-id",
            request_id,
            timeout=30,
        )
        append_jsonl(self.approval_trace, {"action": "get", "request_id": request_id, "payload": payload})
        return payload

    def approval_submit(self, request_id: str) -> None:
        submit_value = {"decision": "approve"}
        payload = self.run_cli(
            "approval",
            "submit",
            "--work-dir",
            str(self.runtime_work),
            "--request-id",
            request_id,
            "--decision",
            "approve",
            "--value-json",
            json.dumps(submit_value, ensure_ascii=False),
            "--comment",
            "real positive e2e auto approval",
            timeout=30,
        )
        append_jsonl(
            self.approval_trace,
            {
                "action": "submit",
                "request_id": request_id,
                "decision": "approve",
                "submit_value": submit_value,
                "payload": payload,
            },
        )

    def extract_request_id(self, status_payload: dict[str, Any]) -> str:
        request_id = status_payload.get("human_request_id")
        if request_id:
            return str(request_id)
        pending = status_payload.get("pending_human_requests") or []
        if isinstance(pending, list) and pending:
            request_id = pending[0].get("request_id")
            if request_id:
                return str(request_id)
        pending_action = status_payload.get("pending_action")
        if isinstance(pending_action, dict):
            request_id = pending_action.get("request_id") or pending_action.get("child_request_id")
            if request_id:
                return str(request_id)
        return ""

    def iter_nested_values(self, payload: Any) -> list[Any]:
        items: list[Any] = [payload]
        if isinstance(payload, dict):
            for value in payload.values():
                items.extend(self.iter_nested_values(value))
        elif isinstance(payload, list):
            for value in payload:
                items.extend(self.iter_nested_values(value))
        return items

    def extract_nested_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for item in self.iter_nested_values(payload):
            if not isinstance(item, dict):
                continue
            for key in keys:
                value = item.get(key)
                if value not in (None, "", []):
                    return value
        return None

    def wait_for_phase_change(
        self,
        previous_phase: str,
        previous_node: str,
        previous_request_id: str,
    ) -> None:
        deadline = time.time() + PHASE_CHANGE_TIMEOUT_SECONDS
        last_status: dict[str, Any] | None = None
        while time.time() < deadline:
            status_payload = self.status()
            last_status = status_payload
            phase = str(status_payload.get("phase") or status_payload.get("status") or "")
            node = str(status_payload.get("current_node") or "")
            request_id = self.extract_request_id(status_payload)
            if phase != previous_phase or node != previous_node or request_id != previous_request_id:
                return
            time.sleep(STATUS_POLL_INTERVAL_SECONDS)
        raise AssertionError(
            f"approval submit 后流程未推进: request_id={previous_request_id}, status={last_status}"
        )

    def auto_approve_until_completed(self) -> list[dict[str, str]]:
        phase_history: list[dict[str, str]] = []
        seen_request_ids: set[str] = set()
        deadline = time.time() + STATUS_TIMEOUT_SECONDS
        while time.time() < deadline:
            status_payload = self.status()
            phase = str(status_payload.get("phase") or status_payload.get("status") or "")
            current_node = str(status_payload.get("current_node") or "")
            phase_history.append({"phase": phase, "current_node": current_node})
            if phase == "completed":
                return phase_history
            if phase in {"failed", "stopped", "cancelled", "timed_out"}:
                raise AssertionError(f"workflow 终态失败: {status_payload}")

            request_id = self.extract_request_id(status_payload)
            if phase == "waiting_human" or request_id:
                self.handle_single_approval(
                    phase=phase,
                    current_node=current_node,
                    request_id=request_id,
                    status_payload=status_payload,
                    seen_request_ids=seen_request_ids,
                )
                continue
            time.sleep(STATUS_POLL_INTERVAL_SECONDS)

        tail = self.run_log.read_text(encoding="utf-8", errors="replace") if self.run_log.exists() else ""
        raise AssertionError(f"场景超时未完成\n{tail[-4000:]}")

    def handle_single_approval(
        self,
        *,
        phase: str,
        current_node: str,
        request_id: str,
        status_payload: dict[str, Any],
        seen_request_ids: set[str],
    ) -> None:
        if not request_id:
            raise AssertionError(f"waiting_human 缺少 request_id: {status_payload}")
        if seen_request_ids and request_id not in seen_request_ids:
            raise AssertionError(f"出现第二个审批 request_id: {request_id}")
        approval_payload = self.approval_get(request_id)
        context = self.extract_nested_value(approval_payload, "context")
        if not isinstance(context, dict):
            raise AssertionError(f"approval context 非 dict: {approval_payload}")
        for field in ("mode", "target_count", "classification_summary", "upgrade_plan_summary", "message"):
            if field not in context:
                raise AssertionError(f"approval context 缺少字段 {field}: {approval_payload}")
        if context.get("mode") != "apply":
            raise AssertionError(f"approval mode 不符合预期: {approval_payload}")
        if context.get("target_count") != 2:
            raise AssertionError(f"approval target_count 不符合预期: {approval_payload}")
        node_id = self.extract_nested_value(approval_payload, "node_id", "approval_node", "current_node") or current_node
        if node_id != "capture_approval_decision":
            raise AssertionError(f"approval 节点不符合预期: {approval_payload}")

        seen_request_ids.add(request_id)
        self.approval_events.append(
            {
                "request_id": request_id,
                "node_id": str(node_id),
                "phase": phase,
            }
        )
        self.approval_submit(request_id)
        self.wait_for_phase_change(phase, current_node, request_id)

    def record_fixture_hashes_after(self) -> None:
        self.fixture_hashes_after = {
            str(self.root_fixture_workflow): sha256_file(self.root_fixture_workflow),
            str(self.confirm_fixture_workflow): sha256_file(self.confirm_fixture_workflow),
        }

    def cleanup_success(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)


@unittest.skipUnless(LGWF_PY.is_file(), f"缺少 LGWF CLI: {LGWF_PY}")
class WorkflowRealPositiveE2ETests(unittest.TestCase):
    maxDiff = None

    def test_real_positive_apply_approve_minimal_placeholder_flow(self) -> None:
        harness = RealPositiveHarness()
        succeeded = False
        phase_history: list[dict[str, str]] = []
        try:
            harness.prepare()
            harness.run_audit()
            harness.start_runtime()
            phase_history = harness.auto_approve_until_completed()
            harness.record_fixture_hashes_after()
            self.assert_black_box_outputs(harness, phase_history)
            succeeded = True
        finally:
            try:
                harness.stop_runtime()
            finally:
                if succeeded:
                    harness.cleanup_success()

    def assert_black_box_outputs(
        self,
        harness: RealPositiveHarness,
        phase_history: list[dict[str, str]],
    ) -> None:
        self.assertEqual("completed", phase_history[-1]["phase"])
        waiting_nodes = [item["current_node"] for item in phase_history if item["phase"] == "waiting_human"]
        self.assertIn("capture_approval_decision", waiting_nodes, phase_history)
        self.assertEqual(1, len(harness.approval_events), harness.approval_events)
        self.assertEqual("capture_approval_decision", harness.approval_events[0]["node_id"])

        report_path = harness.runtime_work / "reports" / "wf-dsl-upgrade" / "report.md"
        self.assertTrue(report_path.is_file(), report_path)
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("mode: apply", report_text)
        self.assertIn("目标数量: 2", report_text)
        self.assertIn("自动计划数: 0", report_text)
        self.assertIn("审批结果: approve", report_text)
        self.assertIn("本报告为初稿占位", report_text)

        result_summary = read_json(harness.runtime_work / ".lgwf" / "result_summary.json", {})
        self.assertEqual("draft", result_summary.get("status"))
        self.assertEqual("approve", result_summary.get("approval", {}).get("decision"))

        approval = read_json(harness.runtime_work / ".lgwf" / "upgrade_plan_approval.json", {})
        self.assertEqual("approve", approval.get("decision"))
        self.assertTrue(approval.get("allow_apply"))

        plan_summary = read_json(harness.runtime_work / ".lgwf" / "upgrade_plan_summary.json", {})
        self.assertEqual("apply", plan_summary.get("mode"))
        self.assertEqual(0, plan_summary.get("plan_count"))
        self.assertTrue(plan_summary.get("empty_plan"))

        for path_text, before_hash in harness.fixture_hashes_before.items():
            after_hash = harness.fixture_hashes_after.get(path_text)
            self.assertEqual(before_hash, after_hash, f"fixture 文件发生变更: {path_text}")

        status_items = [
            json.loads(line)
            for line in harness.status_trace.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        approval_items = [
            json.loads(line)
            for line in harness.approval_trace.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(status_items, "status trace 为空")
        self.assertEqual(2, len(approval_items), approval_items)
        self.assertEqual("get", approval_items[0]["action"])
        self.assertEqual("submit", approval_items[1]["action"])


if __name__ == "__main__":
    unittest.main()
