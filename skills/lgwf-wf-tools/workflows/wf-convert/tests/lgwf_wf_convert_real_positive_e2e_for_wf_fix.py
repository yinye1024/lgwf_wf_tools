from __future__ import annotations

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
SKILL_ROOT = PACKAGE_ROOT.parent.parent
WF_FIX_ENTRY = "skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf"
WF_FIX_WORKFLOW_LGWF = SKILL_ROOT / "workflows" / "wf-fix" / "wf" / "workflow.lgwf"
TARGET_WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
FIXTURE_ROOT = PACKAGE_ROOT / "tests" / "fixtures" / "static_prompt_workflow"
LGWF_PY = SKILL_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
SAFE_APPROVAL_SUBMIT = SKILL_ROOT / "workflows" / "wf-fix" / "scripts" / "safe_approval_submit.py"
STATUS_TIMEOUT_SECONDS = 1800
PHASE_POLL_INTERVAL_SECONDS = 3
PHASE_ADVANCE_TIMEOUT_SECONDS = 60


def write_utf8_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_utf8_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_json_object(text: str) -> dict[str, Any]:
    for line in [text.strip(), *text.splitlines()[::-1]]:
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AssertionError(f"stdout 未包含可解析 JSON object:\n{text}")


def target_input_payload(source_root: Path, target_package_root: str) -> dict[str, Any]:
    return {
        "prompt_convert_target": {
            "target_dir": str(source_root),
            "entry_files": ["README.md", "flow/workflow.md"],
            "target_workflow_name": "static-approval-router",
            "target_package_root": target_package_root,
            "constraints": ["生成 wf-create-fast handoff target 并 handoff 给主 agent", "handoff target 需要保留审批路由业务语义"],
        }
    }


def request_contains(value: Any, needle: str) -> bool:
    target = needle.lower()
    if isinstance(value, dict):
        return any(request_contains(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(request_contains(item, needle) for item in value)
    if isinstance(value, str):
        return target in value.lower()
    return False


def request_id_from_status(status_payload: dict[str, Any]) -> str:
    request_id = status_payload.get("human_request_id")
    if request_id:
        return str(request_id)
    pending_action = status_payload.get("pending_action")
    if isinstance(pending_action, dict):
        request_id = pending_action.get("request_id") or pending_action.get("child_request_id")
        if request_id:
            return str(request_id)
    pending = status_payload.get("pending_human_requests")
    if isinstance(pending, list) and pending:
        first = pending[0]
        if isinstance(first, dict):
            request_id = first.get("request_id")
            if request_id:
                return str(request_id)
    return ""


class RunWfConvertRealPositiveForWfFixE2E(unittest.TestCase):
    maxDiff = None

    def test_wf_fix_can_drive_wf_convert_real_positive_scenario(self) -> None:
        self.require_runtime_prerequisites()
        temp_root = Path(tempfile.mkdtemp(prefix="wf-convert-wf-fix-positive-"))
        source_root = temp_root / "static_prompt_workflow"
        work_dir = temp_root / "wf-fix-runtime"
        target_package_root = f"workflows/generated/e2e-static-approval-router-{temp_root.name}"
        shutil.copytree(FIXTURE_ROOT, source_root)
        work_dir.mkdir(parents=True, exist_ok=True)

        harness = WorkflowRuntimeHarness(work_dir=work_dir)
        last_status: dict[str, Any] | None = None
        cleanup = False
        try:
            start_payload = harness.start()
            session_id = str(start_payload.get("session_id") or "")
            self.assertTrue(session_id, f"run 输出缺少 session_id: {start_payload}")

            handled_requests: set[str] = set()
            deadline = time.time() + STATUS_TIMEOUT_SECONDS
            while time.time() < deadline:
                last_status = harness.status(session_id)
                phase = str(last_status.get("phase") or last_status.get("status") or "")
                if phase == "completed":
                    break
                if phase in {"failed", "stopped"}:
                    raise AssertionError(f"wf-fix 终态失败: {last_status}")

                request_id = request_id_from_status(last_status)
                if request_id and request_id not in handled_requests:
                    request = harness.approval_get(request_id)
                    self.handle_request(
                        harness=harness,
                        request_id=request_id,
                        request=request,
                        source_root=source_root,
                        target_package_root=target_package_root,
                    )
                    handled_requests.add(request_id)
                    session_id = self.wait_for_phase_change(harness, session_id, request_id)
                    continue

                time.sleep(PHASE_POLL_INTERVAL_SECONDS)
            else:
                raise AssertionError(f"等待 wf-fix 完成超时: last_status={last_status}")

            self.assert_self_fix_summary(work_dir)
            self.assert_target_run_succeeded(work_dir)
            self.assert_business_outputs(work_dir, target_package_root)
            cleanup = True
        except Exception as exc:
            raise AssertionError(
                f"{exc}\n"
                f"保留临时目录: {temp_root}\n"
                f"fixture 副本: {source_root}\n"
                f"wf-fix work_dir: {work_dir}\n"
                f"最后状态: {json.dumps(last_status, ensure_ascii=False) if last_status else '<none>'}"
            ) from exc
        finally:
            if last_status and str(last_status.get("phase")) not in {"completed", "failed", "stopped"}:
                pid = last_status.get("pid")
                if isinstance(pid, int) and pid > 0:
                    try:
                        harness.stop(pid)
                    except Exception:
                        pass
            if cleanup:
                shutil.rmtree(temp_root, ignore_errors=True)

    def require_runtime_prerequisites(self) -> None:
        self.assertTrue(FIXTURE_ROOT.is_dir(), f"缺少固定 prompt workflow fixture: {FIXTURE_ROOT}")
        self.assertTrue(TARGET_WORKFLOW_LGWF.is_file(), f"缺少目标 workflow 文件: {TARGET_WORKFLOW_LGWF}")
        self.assertTrue(WF_FIX_WORKFLOW_LGWF.is_file(), f"缺少 wf-fix workflow 文件: {WF_FIX_WORKFLOW_LGWF}")
        self.assertEqual(WF_FIX_ENTRY, "skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf")
        self.assertTrue(LGWF_PY.is_file(), f"缺少 LGWF CLI: {LGWF_PY}")
        self.assertTrue(SAFE_APPROVAL_SUBMIT.is_file(), f"缺少 safe approval submit: {SAFE_APPROVAL_SUBMIT}")
        codex = shutil.which("codex")
        self.assertIsNotNone(codex, "未找到 codex 命令，无法执行真实 Codex 正向 E2E。")
        completed = subprocess.run(
            [codex, "--version"],
            cwd=str(SKILL_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)

    def handle_request(
        self,
        *,
        harness: "WorkflowRuntimeHarness",
        request_id: str,
        request: dict[str, Any],
        source_root: Path,
        target_package_root: str,
    ) -> None:
        request_text = json.dumps(request, ensure_ascii=False)
        business_input = target_input_payload(source_root, target_package_root)
        direct_target_value = business_input["prompt_convert_target"]

        if request_contains(request, "confirm_self_fix_request"):
            harness.approval_submit(
                request_id,
                value={
                    "target_workflow_lgwf": str(TARGET_WORKFLOW_LGWF).replace("\\", "/"),
                    "max_attempts": 5,
                    "ask_main_agent_for_target_approvals": True,
                },
                comment="auto approve self fix request",
            )
            return

        if request_contains(request, "collect_target_workflow_input"):
            harness.approval_submit(
                request_id,
                value=business_input,
                comment="auto submit target workflow input",
            )
            return

        if request_contains(request, "proxy_target_approval"):
            if request_contains(request, "collect_prompt_workflow_target"):
                harness.approval_submit(
                    request_id,
                    value={
                        "decision": "approve",
                        "value": direct_target_value,
                        "comment": "自动确认 collect_prompt_workflow_target",
                    },
                    comment="proxy collect_prompt_workflow_target",
                )
                return

            if request_contains(request, "confirm_create_input"):
                proposal = self.read_required_json(
                    self.current_target_attempt_dir(harness.work_dir) / ".lgwf" / "wf_create_fast_input_proposal.json"
                )
                harness.approval_submit(
                    request_id,
                    value={
                        "decision": "approve",
                        "value": {
                            "decision": "approve",
                            "confirmed": proposal,
                            "comment": "原样确认 proposal",
                        },
                        "comment": "自动确认 confirm_create_input",
                    },
                    comment="proxy confirm_create_input",
                )
                return

        raise AssertionError(f"未知 approval 请求: {request_text}")

    def current_target_attempt_dir(self, work_dir: Path) -> Path:
        target = self.read_required_json(work_dir / ".lgwf" / "self_fix_target.json")
        attempt = int(target.get("current_attempt") or 0)
        self.assertGreater(attempt, 0, f"self_fix_target.current_attempt 非法: {target}")
        return work_dir / ".lgwf" / "target_runs" / f"attempt-{attempt:03d}"

    def read_required_json(self, path: Path) -> dict[str, Any]:
        self.assertTrue(path.is_file(), f"缺少 JSON 产物: {path}")
        value = read_utf8_json(path)
        self.assertIsInstance(value, dict, f"{path} 必须是 JSON object")
        return value

    def wait_for_phase_change(
        self,
        harness: "WorkflowRuntimeHarness",
        session_id: str,
        request_id: str,
    ) -> str:
        deadline = time.time() + PHASE_ADVANCE_TIMEOUT_SECONDS
        last_status: dict[str, Any] | None = None
        while time.time() < deadline:
            last_status = harness.status(session_id)
            pending_id = request_id_from_status(last_status)
            if pending_id != request_id:
                pid = last_status.get("pid")
                if isinstance(pid, int) and not harness.is_process_running(pid):
                    resumed = harness.resume_existing()
                    return str(resumed.get("session_id") or session_id)
                return session_id
            time.sleep(PHASE_POLL_INTERVAL_SECONDS)
        raise AssertionError(f"提交 approval 后流程未推进: request_id={request_id}; status={last_status}")

    def assert_self_fix_summary(self, work_dir: Path) -> None:
        summary = self.read_required_json(work_dir / ".lgwf" / "self_fix_summary.json")
        status = str(summary.get("overall_status") or summary.get("status") or "").lower()
        self.assertIn(
            status,
            {"fixed", "succeeded", "success_clean", "success_degraded", "finish_success", "finish_degraded"},
            f"self_fix_summary 未表明成功: {summary}",
        )
        self.assertNotIn(status, {"waiting_human", "failed", "max_attempts_reached"}, f"self_fix_summary 非成功终态: {summary}")
        self.assertEqual(summary.get("max_attempts"), 5)

        request = self.read_required_json(work_dir / ".lgwf" / "self_fix_request.json")
        self.assertEqual(request.get("target_workflow_lgwf"), str(TARGET_WORKFLOW_LGWF).replace("\\", "/"))
        self.assertEqual(request.get("max_attempts"), 5)
        self.assertTrue(request.get("ask_main_agent_for_target_approvals"))

    def assert_target_run_succeeded(self, work_dir: Path) -> None:
        target = self.read_required_json(work_dir / ".lgwf" / "self_fix_target.json")
        self.assertEqual(target.get("last_status"), "succeeded", f"self_fix_target 未记录成功: {target}")

        observation = self.read_required_json(work_dir / ".lgwf" / "target_repair" / "current" / "observation.json")
        self.assertEqual(observation.get("status"), "succeeded", f"最后一轮 observation 非 succeeded: {observation}")
        status_detail = observation.get("status_detail")
        self.assertIsInstance(status_detail, dict, f"observation 缺少 status_detail: {observation}")
        self.assertEqual(status_detail.get("phase"), "completed", f"最后一轮 target run 非 completed: {observation}")

        attempt_dir = self.current_target_attempt_dir(work_dir)
        history_path = work_dir / ".lgwf" / "self_fix_history.json"
        self.assertTrue(history_path.is_file(), f"缺少 self_fix_history: {history_path}")
        history = read_utf8_json(history_path)
        self.assertIsInstance(history, list, f"self_fix_history 必须是 list: {history}")
        self.assertTrue(any(isinstance(item, dict) and item.get("event") == "target_succeeded" for item in history), history)
        if any(isinstance(item, dict) and item.get("event") == "repair_candidate_promoted" for item in history):
            self.assertTrue(
                any(isinstance(item, dict) and item.get("event") == "fix_attempt_recorded" for item in history),
                f"存在 promote 但缺少 fix_attempt_recorded: {history}",
            )

    def assert_business_outputs(self, work_dir: Path, target_package_root: str) -> None:
        attempt_dir = self.current_target_attempt_dir(work_dir)
        for relative in [
            ".lgwf/prompt_workflow_inspection.json",
            ".lgwf/wf_create_fast_input_proposal.json",
            ".lgwf/wf_create_fast_input.json",
            ".lgwf/wf_create_fast_handoff.json",
        ]:
            self.assertTrue((attempt_dir / relative).is_file(), f"缺少目标 workflow 黑盒产物: {relative}")
        for relative in [
            ".lgwf/wf_create_fast_payload.json",
            ".lgwf/wf_create_fast_input_for_wf_create_fast.json",
        ]:
            self.assertFalse((attempt_dir / relative).exists(), f"不应再生成旧目标 workflow 产物: {relative}")

        handoff_target = self.read_required_json(attempt_dir / ".lgwf" / "wf_create_fast_handoff.json")
        self.assertEqual(handoff_target.get("input_mode"), "converted_contract")
        self.assertEqual(handoff_target.get("target_package_root"), target_package_root)
        self.assertNotIn("source_root", handoff_target)
        self.assertNotIn("request", handoff_target)
        combined = json.dumps(handoff_target, ensure_ascii=False).lower()
        self.assertIn(target_package_root.lower(), combined)
        for keyword in ["approval", "risk", "audit"]:
            self.assertIn(keyword, combined, f"handoff target 未保留业务关键词 {keyword}: {handoff_target}")
        self.assertTrue(
            "human_review" in combined or "human review" in combined or "人工" in combined,
            f"handoff target 未体现人工复核分支: {handoff_target}",
        )
        self.assertTrue(
            "auto_approve" in combined or "auto approve" in combined or "自动" in combined,
            f"handoff target 未体现自动通过分支: {handoff_target}",
        )
        pending_files = sorted((attempt_dir / ".lgwf" / "handoff").glob("*.pending.json"))
        self.assertTrue(pending_files, "缺少目标 workflow handoff pending 文件")
        pending = self.read_required_json(pending_files[-1])
        pending_text = json.dumps(pending, ensure_ascii=False)
        self.assertIn("wf_create_fast_launch_input", pending_text)
        self.assertEqual(
            pending["input_json_file"],
            str((attempt_dir / ".lgwf" / "wf_create_fast_launch_input.json").resolve()),
        )
        self.assertIn("target_file", pending_text)
        self.assertIn("wf_create_fast_handoff.json", pending_text.replace("\\", "/"))


class WorkflowRuntimeHarness:
    def __init__(self, *, work_dir: Path) -> None:
        self.work_dir = work_dir
        self.python = shutil.which("python") or "python"

    def run_command(self, args: list[str], *, timeout: int = 300) -> dict[str, Any]:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        completed = subprocess.run(
            [self.python, str(LGWF_PY), *args],
            cwd=str(SKILL_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "命令执行失败:\n"
                f"command={[self.python, str(LGWF_PY), *args]}\n"
                f"stdout={completed.stdout}\n"
                f"stderr={completed.stderr}"
            )
        return parse_json_object(completed.stdout)

    def start(self) -> dict[str, Any]:
        return self.run_command(
            [
                "run",
                "--workflow-lgwf",
                str(WF_FIX_WORKFLOW_LGWF),
                "--work-dir",
                str(self.work_dir),
                "--input-json",
                "{}",
                "--background",
            ],
            timeout=120,
        )

    def resume_existing(self) -> dict[str, Any]:
        return self.run_command(
            [
                "run",
                "--workflow-json",
                str(self.work_dir / ".lgwf" / "workflow" / "workflow.json"),
                "--work-dir",
                str(self.work_dir),
                "--input-json",
                "{}",
                "--background",
                "--resume-existing",
            ],
            timeout=120,
        )

    def status(self, session_id: str) -> dict[str, Any]:
        return self.run_command(["status", "--work-dir", str(self.work_dir), "--session-id", session_id])

    def approval_get(self, request_id: str) -> dict[str, Any]:
        return self.run_command(["approval", "get", "--work-dir", str(self.work_dir), "--request-id", request_id])

    def is_process_running(self, pid: int) -> bool:
        if os.name == "nt":
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            return completed.returncode == 0 and str(pid) in completed.stdout
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def approval_submit(self, request_id: str, *, value: dict[str, Any], comment: str) -> dict[str, Any]:
        value_path = self.work_dir / ".lgwf" / "approval-values" / f"{request_id}.json"
        write_utf8_json(value_path, value)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        completed = subprocess.run(
            [
                self.python,
                str(SAFE_APPROVAL_SUBMIT),
                "--work-dir",
                str(self.work_dir),
                "--request-id",
                request_id,
                "--decision",
                "approve",
                "--value-file",
                str(value_path),
                "--comment",
                comment,
            ],
            cwd=str(SKILL_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "approval 提交失败:\n"
                f"command={[self.python, str(SAFE_APPROVAL_SUBMIT), '--work-dir', str(self.work_dir), '--request-id', request_id]}\n"
                f"stdout={completed.stdout}\n"
                f"stderr={completed.stderr}"
            )
        return parse_json_object(completed.stdout)

    def stop(self, pid: int) -> dict[str, Any]:
        return self.run_command(["stop", "--pid", str(pid)], timeout=60)


if __name__ == "__main__":
    unittest.main()
