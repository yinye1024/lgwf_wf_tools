from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[4]
SOURCE_WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
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
RUNTIME_TRACE_DIRNAME = ".lgwf-test"


def run_lgwf(args: list[str], *, env: dict[str, str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(LGWF_PY), *args],
        cwd=REPO_ROOT,
        env=env,
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
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and (required_keys is None or required_keys.issubset(data)):
            matches.append(data)
    if matches:
        return matches[-1]
    expected = f" with keys {sorted(required_keys)}" if required_keys else ""
    raise AssertionError(f"stdout 未包含 JSON object{expected}:\n{text}")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_prompt_file_mode_patch(patch_dir: Path) -> None:
    patch_dir.mkdir(parents=True, exist_ok=True)
    (patch_dir / "sitecustomize.py").write_text(
        r'''
from __future__ import annotations

import json
import os
import pathlib
import uuid


def _extract_main_prompt_path(handoff: str) -> str:
    lines = handoff.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() == "Main prompt file:":
            return lines[index + 1].strip().replace("\\", "/")
    return ""


if os.environ.get("LGWF_FAKE_CODEX_PROMPT_FILE_MODE") == "1":
    import lgwf_client.process_execution as process_execution

    _original_resolve = process_execution.CommandResolver.resolve

    def _resolve_with_prompt_file(self, command):
        if (
            isinstance(command, list)
            and len(command) >= 2
            and str(command[0]).lower() == "codex"
            and isinstance(command[-1], str)
            and command[-1].startswith("# LGWF Codex Handoff")
        ):
            work_dir = pathlib.Path(os.environ.get("LGWF_FAKE_CODEX_WORK_DIR") or pathlib.Path.cwd())
            prompt_root = work_dir / ".lgwf" / "fake_codex_prompts" / uuid.uuid4().hex
            prompt_root.mkdir(parents=True, exist_ok=True)
            prompt_path = prompt_root / "handoff_prompt.txt"
            prompt_path.write_text(command[-1], encoding="utf-8")
            metadata = {
                "main_prompt_file": _extract_main_prompt_path(command[-1]),
                "cwd": str(work_dir),
                "argv": command,
            }
            (prompt_root / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            command = [*command[:-1], "--prompt-file", str(prompt_path)]
        return _original_resolve(self, command)

    process_execution.CommandResolver.resolve = _resolve_with_prompt_file
'''.lstrip(),
        encoding="utf-8",
    )


def write_fake_codex(fake_bin: Path) -> None:
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_py = fake_bin / "fake_codex.py"
    fake_py.write_text(
        r'''
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


def write_json(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def extract_prompt(argv: list[str]) -> tuple[str, pathlib.Path | None]:
    prompt_path: pathlib.Path | None = None
    for index, arg in enumerate(argv[1:], start=1):
        if arg == "--prompt-file" and index + 1 < len(argv):
            prompt_path = pathlib.Path(argv[index + 1])
            return prompt_path.read_text(encoding="utf-8"), prompt_path
        if arg.startswith("--prompt-file="):
            prompt_path = pathlib.Path(arg.split("=", 1)[1])
            return prompt_path.read_text(encoding="utf-8"), prompt_path
    stdin_text = sys.stdin.read()
    return stdin_text, prompt_path


def extract_main_prompt_file(prompt_text: str) -> str:
    lines = prompt_text.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() == "Main prompt file:":
            return lines[index + 1].strip().replace("\\", "/")
    return ""


def load_metadata(prompt_path: pathlib.Path | None) -> dict[str, Any]:
    if prompt_path is None:
        return {}
    metadata_path = prompt_path.parent / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def next_call_index(root: pathlib.Path, node_key: str) -> int:
    state_path = root / ".lgwf" / "fake_codex_call_state.json"
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    state[node_key] = int(state.get(node_key, 0)) + 1
    write_json(state_path, state)
    return int(state[node_key])


def main(argv: list[str]) -> int:
    prompt_text, prompt_path = extract_prompt(argv)
    metadata = load_metadata(prompt_path)
    root = pathlib.Path(str(metadata.get("cwd") or pathlib.Path.cwd()))
    main_prompt_file = str(metadata.get("main_prompt_file") or extract_main_prompt_file(prompt_text))
    node_key = main_prompt_file or "<stdin>"
    call_index = next_call_index(root, node_key)
    calls_path = root / ".lgwf" / "fake_codex_calls.jsonl"
    unexpected_path = root / ".lgwf" / "fake_codex_unexpected_call.json"
    payload = {
        "main_prompt_file": main_prompt_file,
        "instruction_id": metadata.get("instruction_id", ""),
        "argv": argv[1:],
        "call_index": call_index,
        "cwd": str(root),
        "summary": "wf-dsl-upgrade 当前不存在 codex_like_nodes；任何 Codex 调用都视为契约外行为。",
    }
    append_jsonl(calls_path, payload)
    write_json(unexpected_path, payload)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''.lstrip(),
        encoding="utf-8",
    )
    for name in ("codex.cmd", "codex.bat"):
        (fake_bin / name).write_text(f'@echo off\r\npython "%~dp0fake_codex.py" %*\r\n', encoding="utf-8")


def write_fake_skill_dir(root: Path) -> Path:
    skill_dir = root / "lgwf-client-assist"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "AGENTS.md").write_text("# lgwf-client-assist\n", encoding="utf-8")
    return skill_dir


def copy_target_package(destination: Path) -> None:
    shutil.copytree(
        PACKAGE_ROOT,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", ".lgwf", "ws", "ws_*"),
    )


class WorkflowRuntimeHarness:
    def __init__(self, *, temp_root: Path, scenario: dict[str, Any]) -> None:
        self.temp_root = temp_root
        self.scenario = scenario
        self.patch_dir = temp_root / "pythonpath"
        self.fake_bin = temp_root / "fake_bin"
        self.skill_dir = temp_root / "client_assist"
        self.work_dir = temp_root / "runtime"
        self.package_root = temp_root / "isolated_package"
        self.workflow_lgwf = self.package_root / "wf" / "workflow.lgwf"
        self.log_file = self.work_dir / ".lgwf" / "runtime_fake.log"
        self.status_log = self.work_dir / RUNTIME_TRACE_DIRNAME / "status_trace.jsonl"
        self.approval_log = self.work_dir / RUNTIME_TRACE_DIRNAME / "approval_trace.jsonl"
        self.command_log = self.work_dir / RUNTIME_TRACE_DIRNAME / "command_trace.jsonl"
        self.runtime_env = self._prepare()

    def _prepare(self) -> dict[str, str]:
        write_prompt_file_mode_patch(self.patch_dir)
        write_fake_codex(self.fake_bin)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        copy_target_package(self.package_root)
        skill_dir = write_fake_skill_dir(self.skill_dir)

        env = dict(os.environ)
        env["PATH"] = str(self.fake_bin) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(self.patch_dir) + os.pathsep + env.get("PYTHONPATH", "")
        env["LGWF_FAKE_CODEX_WORK_DIR"] = str(self.work_dir)
        env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
        env["LGWF_CLIENT_ASSIST"] = str(skill_dir)
        env["LGWF_CLIENT_ASSIST_SKILL_DIR"] = str(skill_dir)
        env["LGWF_ALLOW_TEST_CLIENT_ASSIST_ENV"] = "1"
        return env

    def build_input_payload(self) -> dict[str, Any]:
        approval_workflow = self.package_root / "wf" / "05_confirm_upgrade_plan" / "workflow.lgwf"
        return {
            "scope_mode": "registry",
            "targets": [str(self.workflow_lgwf), str(approval_workflow)],
            "max_targets": 8,
            "mode": "apply",
        }

    def run_cli(self, *args: str, timeout: int = 30) -> dict[str, Any]:
        command = list(args)
        append_jsonl(self.command_log, {"command": command})
        completed = run_lgwf(command, env=self.runtime_env, timeout=timeout)
        append_jsonl(
            self.command_log,
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"命令失败: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return parse_json_object(completed.stdout)

    def start(self) -> tuple[str, int | None]:
        input_path = self.temp_root / "scenario_input.json"
        write_json(input_path, self.build_input_payload())
        payload = self.run_cli(
            "run",
            "--workflow-lgwf",
            str(self.workflow_lgwf),
            "--work-dir",
            str(self.work_dir),
            "--input-json-file",
            str(input_path),
            "--background",
            "--log-file",
            str(self.log_file),
        )
        session_id = str(payload.get("session_id") or payload.get("session-id") or "")
        if not session_id:
            raise AssertionError(f"run 输出缺少 session_id: {payload}")
        pid_value = payload.get("pid")
        pid = int(pid_value) if isinstance(pid_value, int | float) or str(pid_value).isdigit() else None
        return session_id, pid

    def stop(self, pid: int | None) -> None:
        if pid is None:
            return
        run_lgwf(["stop", "--pid", str(pid)], env=self.runtime_env, timeout=30)

    def wait_for_exit(self, pid: int | None, *, timeout_seconds: int = 10) -> None:
        if pid is None:
            return
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if completed.returncode != 0:
                return
            if str(pid) not in completed.stdout:
                return
            time.sleep(0.5)

    def status(self, session_id: str) -> dict[str, Any]:
        payload = self.run_cli("status", "--work-dir", str(self.work_dir), "--session-id", session_id)
        phase = payload.get("phase") or payload.get("status")
        if not phase:
            raise AssertionError(f"status 输出缺少 phase/status: {payload}")
        append_jsonl(self.status_log, payload)
        return payload

    def approval_get(self, request_id: str) -> dict[str, Any]:
        payload = self.run_cli("approval", "get", "--work-dir", str(self.work_dir), "--request-id", request_id)
        append_jsonl(self.approval_log, {"action": "get", "payload": payload})
        return payload

    def approval_submit(self, request_id: str, *, decision: str, submit_value: dict[str, Any]) -> dict[str, Any]:
        payload = self.run_cli(
            "approval",
            "submit",
            "--work-dir",
            str(self.work_dir),
            "--request-id",
            request_id,
            "--decision",
            decision,
            "--value-json",
            json.dumps(submit_value, ensure_ascii=False),
            "--comment",
            "runtime fake e2e auto approval",
        )
        append_jsonl(
            self.approval_log,
            {
                "action": "submit",
                "request_id": request_id,
                "decision": decision,
                "submit_value": submit_value,
                "payload": payload,
            },
        )
        return payload


@unittest.skipUnless(LGWF_PY.is_file(), f"缺少 LGWF CLI: {LGWF_PY}")
class WorkflowRuntimeFakeE2ETests(unittest.TestCase):
    maxDiff = None

    def cleanup_runtime(self, harness: WorkflowRuntimeHarness, pid: int | None, stack: ExitStack) -> None:
        try:
            harness.stop(pid)
            harness.wait_for_exit(pid)
        finally:
            stack.close()

    def run_scenario(self, scenario: dict[str, Any]) -> tuple[WorkflowRuntimeHarness, list[dict[str, Any]], list[dict[str, Any]]]:
        stack = ExitStack()
        temp_root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=f"wf-dsl-upgrade-{scenario['scenario_id']}-")))
        harness = WorkflowRuntimeHarness(temp_root=temp_root, scenario=scenario)
        session_id, pid = harness.start()
        self.addCleanup(self.cleanup_runtime, harness, pid, stack)

        phase_history: list[dict[str, Any]] = []
        approval_events: list[dict[str, Any]] = []
        repeat_counts: dict[str, int] = {}
        deadline = time.time() + STATUS_TIMEOUT_SECONDS

        while time.time() < deadline:
            status = harness.status(session_id)
            phase = str(status.get("phase") or status.get("status"))
            current_node = str(status.get("current_node") or "")
            phase_history.append({"phase": phase, "current_node": current_node})
            if phase == "completed":
                return harness, phase_history, approval_events
            if phase in {"failed", "stopped", "cancelled", "timed_out"}:
                raise AssertionError(f"workflow 终态失败: {status}")

            request_id = self.extract_request_id(status, required=False)
            if phase == "waiting_human" or request_id:
                if not request_id:
                    raise AssertionError(f"waiting_human 缺少 request_id: {status}")
                repeat_counts[request_id] = repeat_counts.get(request_id, 0) + 1
                self.assertLessEqual(repeat_counts[request_id], 3, f"同一 request_id 连续无进展: {status}")
                self.assertEqual(0, len(approval_events), f"出现额外审批节点: {approval_events}")
                approval_payload = harness.approval_get(request_id)
                node_id = self.assert_approval_payload(approval_payload, fallback_node=current_node)
                decision = str(scenario["approval_steps"][0]["decision"])
                submit_value = scenario["approval_steps"][0]["submit_value"]
                approval_events.append(
                    {
                        "request_id": request_id,
                        "node_id": node_id,
                        "decision": decision,
                    }
                )
                harness.approval_submit(request_id, decision=decision, submit_value=submit_value)
                self.wait_for_phase_change(
                    harness=harness,
                    session_id=session_id,
                    previous_phase=phase,
                    previous_node=current_node,
                    previous_request_id=request_id,
                )
                continue
            time.sleep(STATUS_POLL_INTERVAL_SECONDS)

        log_tail = harness.log_file.read_text(encoding="utf-8", errors="replace") if harness.log_file.exists() else ""
        raise AssertionError(f"场景超时未完成: {scenario['scenario_id']}\n{log_tail[-4000:]}")

    def wait_for_phase_change(
        self,
        *,
        harness: WorkflowRuntimeHarness,
        session_id: str,
        previous_phase: str,
        previous_node: str,
        previous_request_id: str,
    ) -> None:
        deadline = time.time() + PHASE_CHANGE_TIMEOUT_SECONDS
        last_status: dict[str, Any] | None = None
        while time.time() < deadline:
            status = harness.status(session_id)
            last_status = status
            phase = str(status.get("phase") or status.get("status"))
            current_node = str(status.get("current_node") or "")
            request_id = self.extract_request_id(status, required=False)
            if phase != previous_phase or current_node != previous_node or request_id != previous_request_id:
                return
            time.sleep(STATUS_POLL_INTERVAL_SECONDS)
        raise AssertionError(
            f"approval submit 后 20 秒内流程未前进: request_id={previous_request_id}, last_status={last_status}"
        )

    def extract_request_id(self, status: dict[str, Any], *, required: bool) -> str:
        request_id = status.get("human_request_id")
        if request_id:
            return str(request_id)
        pending = status.get("pending_human_requests") or []
        if isinstance(pending, list) and pending:
            candidate = pending[0].get("request_id")
            if candidate:
                return str(candidate)
        pending_action = status.get("pending_action")
        if isinstance(pending_action, dict):
            candidate = pending_action.get("request_id") or pending_action.get("child_request_id")
            if candidate:
                return str(candidate)
        if required:
            raise AssertionError(f"status 缺少 request_id: {status}")
        return ""

    def iter_nested_values(self, payload: Any) -> list[Any]:
        values: list[Any] = [payload]
        if isinstance(payload, dict):
            for value in payload.values():
                values.extend(self.iter_nested_values(value))
        elif isinstance(payload, list):
            for value in payload:
                values.extend(self.iter_nested_values(value))
        return values

    def extract_approval_value(self, approval_payload: dict[str, Any], *keys: str) -> Any:
        for item in self.iter_nested_values(approval_payload):
            if not isinstance(item, dict):
                continue
            for key in keys:
                value = item.get(key)
                if value not in (None, "", []):
                    return value
        return None

    def extract_approval_node_id(self, approval_payload: dict[str, Any], *, fallback: str) -> str:
        value = self.extract_approval_value(
            approval_payload,
            "node_id",
            "approval_node",
            "current_node",
        )
        if value:
            return str(value)
        return fallback

    def assert_approval_payload(self, approval_payload: dict[str, Any], *, fallback_node: str) -> str:
        request_id = self.extract_approval_value(approval_payload, "request_id")
        self.assertTrue(request_id, approval_payload)
        prompt = self.extract_approval_value(approval_payload, "prompt")
        self.assertTrue(str(prompt or ""), approval_payload)
        context = self.extract_approval_value(approval_payload, "context")
        self.assertIsInstance(context, dict, approval_payload)
        node_id = self.extract_approval_node_id(approval_payload, fallback=fallback_node)
        self.assertEqual("capture_approval_decision", node_id)
        for field in ("mode", "target_count", "classification_summary", "upgrade_plan_summary", "message"):
            self.assertIn(field, context, approval_payload)
        return node_id

    def assert_common_artifacts(self, harness: WorkflowRuntimeHarness, *, scenario_id: str, approval_decision: str) -> None:
        work_dir = harness.work_dir
        target_manifest = read_json(work_dir / ".lgwf" / "target_manifest.json")
        self.assertTrue(target_manifest, "missing target_manifest")
        self.assertTrue(target_manifest["authorized"])
        self.assertEqual(2, len(target_manifest["targets"]))
        for target in target_manifest["targets"]:
            resolved = Path(target).resolve()
            self.assertTrue(str(resolved).startswith(str(harness.package_root.resolve())), target)

        target_validation = read_json(work_dir / ".lgwf" / "target_scope_validation.json")
        self.assertTrue(target_validation["passed"])
        self.assertEqual(2, target_validation["target_count"])

        batch_result = read_json(work_dir / ".lgwf" / "batch_audit_result.json")
        self.assertEqual(2, len(batch_result["targets"]))

        batch_stats = read_json(work_dir / ".lgwf" / "batch_audit_stats.json")
        self.assertEqual(2, batch_stats["target_count"])
        self.assertEqual(2, batch_stats["placeholder_count"])

        classified = read_json(work_dir / ".lgwf" / "classified_findings.json")
        self.assertEqual(2, len(classified["findings"]))
        self.assertTrue(all(item["classification"] == "manual_review" for item in classified["findings"]))

        classification_summary = read_json(work_dir / ".lgwf" / "classification_summary.json")
        self.assertEqual(0, classification_summary["auto_fixable"])
        self.assertEqual(2, classification_summary["manual_review"])

        upgrade_plan = read_json(work_dir / ".lgwf" / "upgrade_plan.json")
        self.assertEqual([], upgrade_plan["items"])

        plan_summary = read_json(work_dir / ".lgwf" / "upgrade_plan_summary.json")
        self.assertEqual("apply", plan_summary["mode"])
        self.assertEqual(0, plan_summary["plan_count"])
        self.assertTrue(plan_summary["empty_plan"])

        approval_context = read_json(work_dir / ".lgwf" / "upgrade_plan_confirmation_context.json")
        for field in ("mode", "target_count", "classification_summary", "upgrade_plan_summary", "message"):
            self.assertIn(field, approval_context)

        approval = read_json(work_dir / ".lgwf" / "upgrade_plan_approval.json")
        self.assertEqual(approval_decision, approval["decision"])
        self.assertEqual("apply", approval["mode"])
        self.assertEqual(approval_decision == "approve", approval["allow_apply"])

        diff_summary = read_json(work_dir / ".lgwf" / "post_upgrade_diff_summary.json")
        self.assertEqual(0, diff_summary["modified_count"])
        self.assertEqual(0, diff_summary["resolved_count"])
        self.assertEqual(0, diff_summary["remaining_count"])

        result_summary = read_json(work_dir / ".lgwf" / "result_summary.json")
        self.assertEqual("draft", result_summary["status"])
        self.assertEqual(approval_decision, result_summary["approval"]["decision"])

        report_path = work_dir / "reports" / "wf-dsl-upgrade" / "report.md"
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("mode: apply", report_text)
        self.assertIn(f"审批结果: {approval_decision}", report_text)

        calls_path = work_dir / ".lgwf" / "fake_codex_calls.jsonl"
        if calls_path.exists():
            calls = [line for line in calls_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual([], calls, f"{scenario_id} 不应触发 fake Codex")
        self.assertFalse((work_dir / ".lgwf" / "fake_codex_unexpected_call.json").exists())

        status_trace = work_dir / RUNTIME_TRACE_DIRNAME / "status_trace.jsonl"
        approval_trace = work_dir / RUNTIME_TRACE_DIRNAME / "approval_trace.jsonl"
        self.assertTrue(status_trace.is_file(), "missing status trace")
        self.assertTrue(approval_trace.is_file(), "missing approval trace")
        status_items = read_jsonl(status_trace)
        approval_items = read_jsonl(approval_trace)
        self.assertTrue(status_items, "empty status trace")
        self.assertEqual(2, len(approval_items), approval_items)
        self.assertEqual("get", approval_items[0]["action"])
        self.assertEqual("submit", approval_items[1]["action"])
        self.assertEqual(approval_decision, approval_items[1]["decision"])
        self.assertEqual("completed", status_items[-1]["phase"])
        if "running" in status_items[-1]:
            self.assertFalse(status_items[-1]["running"])

    def test_happy_path(self) -> None:
        scenario = {
            "scenario_id": "happy_path",
            "approval_steps": [
                {
                    "approval_node": "capture_approval_decision",
                    "decision": "approve",
                    "submit_value": {"decision": "approve"},
                }
            ],
        }
        harness, phase_history, approval_events = self.run_scenario(scenario)
        self.assertEqual("completed", phase_history[-1]["phase"])
        waiting_nodes = [item["current_node"] for item in phase_history if item["phase"] == "waiting_human"]
        self.assertIn("capture_approval_decision", waiting_nodes, phase_history)
        self.assertEqual(1, len(approval_events))
        self.assertEqual("capture_approval_decision", approval_events[0]["node_id"])
        self.assertEqual("approve", approval_events[0]["decision"])
        self.assert_common_artifacts(harness, scenario_id="happy_path", approval_decision="approve")

        applied = read_json(harness.work_dir / ".lgwf" / "applied_changes.json")
        self.assertEqual("placeholder", applied["status"])

        applied_manifest = read_json(harness.work_dir / ".lgwf" / "applied_target_manifest.json")
        self.assertEqual([], applied_manifest["targets"])

        post_upgrade_result = read_json(harness.work_dir / ".lgwf" / "post_upgrade_audit_result.json")
        self.assertEqual("skipped", post_upgrade_result["status"])

    def test_approval_reject_blocks_apply(self) -> None:
        scenario = {
            "scenario_id": "approval_reject_blocks_apply",
            "approval_steps": [
                {
                    "approval_node": "capture_approval_decision",
                    "decision": "reject",
                    "submit_value": {"decision": "reject"},
                }
            ],
        }
        harness, phase_history, approval_events = self.run_scenario(scenario)
        self.assertEqual("completed", phase_history[-1]["phase"])
        self.assertEqual(1, len(approval_events))
        self.assertEqual("capture_approval_decision", approval_events[0]["node_id"])
        self.assertEqual("reject", approval_events[0]["decision"])
        self.assert_common_artifacts(harness, scenario_id="approval_reject_blocks_apply", approval_decision="reject")

        applied = read_json(harness.work_dir / ".lgwf" / "applied_changes.json")
        self.assertEqual("skipped", applied["status"])
        self.assertEqual([], applied["items"])

        applied_manifest = read_json(harness.work_dir / ".lgwf" / "applied_target_manifest.json")
        self.assertEqual([], applied_manifest["targets"])
        self.assertIn("未获 apply 授权", applied_manifest["reason"])

        post_upgrade_result = read_json(harness.work_dir / ".lgwf" / "post_upgrade_audit_result.json")
        self.assertEqual("skipped", post_upgrade_result["status"])
        self.assertEqual([], post_upgrade_result["targets"])


if __name__ == "__main__":
    unittest.main()
