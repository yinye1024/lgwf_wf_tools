from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = PACKAGE_ROOT.parents[1]
REPO_ROOT = FACADE_ROOT.parents[1]
WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
LGWF = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    raise AssertionError(f"stdout 未包含 JSON object: {text}")


def run_lgwf(args: list[str], *, env: dict[str, str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [os.sys.executable, str(LGWF), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def make_target_package(root: Path) -> dict[str, Any]:
    package_root = root / "runtime-target"
    package_root.mkdir()
    workflow_lgwf = package_root / "workflow.lgwf"
    workflow_lgwf.write_text("WORKFLOW runtime_target;\nENTRY noop;\n", encoding="utf-8")
    tests_dir = package_root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_runtime_target_script_flow_e2e.py").write_text("print('script ok')\n", encoding="utf-8")
    (tests_dir / "test_runtime_target_runtime_fake_e2e.py").write_text("print('runtime ok')\n", encoding="utf-8")
    return {
        "target_workflow_lgwf": str(workflow_lgwf),
        "target_package_root": str(package_root),
        "target_dirs": [str(package_root)],
        "mode": "manual",
    }


def write_runtime_patch(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "sitecustomize.py").write_text(
        textwrap.dedent(
            r"""
            from __future__ import annotations

            import json
            import os
            import pathlib
            import sys


            def _read_state_path(state, path):
                current = state
                for part in str(path).split("."):
                    if not isinstance(current, dict):
                        return None
                    current = current.get(part)
                return current


            def _write_state_path(state, path, value):
                current = state
                parts = str(path).split(".")
                for part in parts[:-1]:
                    child = current.get(part)
                    if not isinstance(child, dict):
                        child = {}
                        current[part] = child
                    current = child
                current[parts[-1]] = value
                return state


            class _FakeRunWorkflowCapability:
                name = "flow.run_workflow"

                def create_node(self, node_id, config):
                    def node(state):
                        work_dir = pathlib.Path(os.environ["LGWF_POST_FIX_FAKE_WORK_DIR"])
                        input_path = config["input_path"]
                        result_path = config["result_path"]
                        child_input = _read_state_path(state, input_path)
                        record = {
                            "node_id": node_id,
                            "workflow_lgwf": config["workflow_lgwf"],
                            "declared_work_dir": config["work_dir"],
                            "input": child_input,
                            "status": "completed",
                            "fake": True,
                        }
                        trace_path = work_dir / ".lgwf-test" / "run_workflow_trace.jsonl"
                        trace_path.parent.mkdir(parents=True, exist_ok=True)
                        with trace_path.open("a", encoding="utf-8") as handle:
                            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        return _write_state_path(dict(state), result_path, record)

                    return node


            def _patch_registry(module):
                if getattr(module, "_post_fix_fake_run_workflow_patched", False):
                    return
                registry = getattr(module, "REGISTRY", None)
                if isinstance(registry, dict):
                    registry["flow.run_workflow"] = _FakeRunWorkflowCapability()
                    module._post_fix_fake_run_workflow_patched = True


            _original_import = __import__


            def _import_with_patch(name, globals=None, locals=None, fromlist=(), level=0):
                module = _original_import(name, globals, locals, fromlist, level)
                registry_module = sys.modules.get("lgwf.capabilities.registry")
                if registry_module is not None:
                    _patch_registry(registry_module)
                return module


            __builtins__["__import__"] = _import_with_patch
            existing_registry = sys.modules.get("lgwf.capabilities.registry")
            if existing_registry is not None:
                _patch_registry(existing_registry)
            """
        ).lstrip(),
        encoding="utf-8",
    )


@unittest.skipUnless(LGWF.is_file(), f"LGWF facade not found: {LGWF}")
class LgwfWfPostFixRuntimeFakeE2ETest(unittest.TestCase):
    maxDiff = None

    def prepare_runtime(self, stack: ExitStack) -> tuple[dict[str, str], Path, Path, dict[str, Any]]:
        temp = stack.enter_context(tempfile.TemporaryDirectory(prefix="lgwf-post-fix-runtime-fake-", ignore_cleanup_errors=True))
        temp_root = Path(temp)
        work_dir = temp_root / "work"
        work_dir.mkdir()
        patch_dir = temp_root / "pythonpath"
        write_runtime_patch(patch_dir)
        target = make_target_package(temp_root)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(patch_dir) + os.pathsep + env.get("PYTHONPATH", "")
        env["LGWF_POST_FIX_FAKE_WORK_DIR"] = str(work_dir)
        return env, work_dir, temp_root / "workflow.log", target

    def wait_status(
        self,
        *,
        pid: int,
        work_dir: Path,
        env: dict[str, str],
        timeout_seconds: int = 30,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            status = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], env=env)
            self.assertEqual(status.returncode, 0, status.stderr + status.stdout)
            last = parse_json_object(status.stdout, {"running"})
            if (
                last.get("running") is False
                or last.get("phase") in {"waiting_human", "waiting_choice", "completed", "failed"}
                or last.get("human_request_id")
                or last.get("pending_human_requests")
            ):
                return last
            time.sleep(0.5)
        raise AssertionError(f"workflow status timeout: {last}")

    def request_id(self, status: dict[str, Any]) -> str:
        pending = status.get("pending_human_requests") or []
        if pending:
            return str(pending[0]["request_id"])
        if status.get("human_request_id"):
            return str(status["human_request_id"])
        pending_action = status.get("pending_action")
        if isinstance(pending_action, dict):
            candidate = pending_action.get("request_id") or pending_action.get("child_request_id")
            if candidate:
                return str(candidate)
        raise AssertionError(f"status 缺少 request_id: {status}")

    def submit_approval(
        self,
        *,
        work_dir: Path,
        env: dict[str, str],
        request_id: str,
        value: dict[str, Any],
    ) -> None:
        submit = run_lgwf(
            [
                "approval",
                "submit",
                "--work-dir",
                str(work_dir),
                "--request-id",
                request_id,
                "--decision",
                "approve",
                "--comment",
                "runtime fake approval",
            ],
            env=env,
        )
        self.assertEqual(submit.returncode, 0, submit.stderr + submit.stdout)

    def submit_choice(
        self,
        *,
        work_dir: Path,
        env: dict[str, str],
        request_id: str,
        route: str,
    ) -> None:
        from lgwf import human_approval

        payload = {
            "request_id": request_id,
            "decision": "approve",
            "value": {"decision": route, "reason": f"runtime fake selected {route}"},
            "created_by": "main_agent_ask",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        human_approval.write_controller_payload(work_dir, request_id, payload)
        human_approval.submit_controller_payload(work_dir, request_id, final_user_confirmed=True)

    def wait_for_request_change(
        self,
        *,
        pid: int,
        work_dir: Path,
        env: dict[str, str],
        previous_request_id: str,
        timeout_seconds: int = 20,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        last: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            status = self.wait_status(pid=pid, work_dir=work_dir, env=env, timeout_seconds=5)
            last = status
            if status.get("running") is False or status.get("phase") in {"completed", "failed"}:
                return
            pending_ids = [
                item.get("request_id")
                for item in status.get("pending_human_requests", [])
                if isinstance(item, dict) and item.get("request_id")
            ]
            if pending_ids and previous_request_id not in pending_ids:
                return
            try:
                current_request_id = self.request_id(status)
            except AssertionError:
                return
            if current_request_id != previous_request_id:
                return
            time.sleep(0.5)
        raise AssertionError(f"request {previous_request_id} submit 后未前进: {last}")

    def read_human_request(self, *, work_dir: Path, request_id: str) -> dict[str, Any]:
        request_path = work_dir / ".lgwf" / "human" / f"{request_id}.request.json"
        self.assertTrue(request_path.is_file(), request_path)
        return read_json(request_path)

    def test_manual_run_auto_then_skip_manual_real_stages(self) -> None:
        with ExitStack() as stack:
            env, work_dir, log_file, target = self.prepare_runtime(stack)
            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(WORKFLOW_LGWF),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    json.dumps({"post_fix_target": target}, ensure_ascii=False),
                    "--background",
                    "--log-file",
                    str(log_file),
                ],
                env=env,
                timeout=60,
            )
            self.assertEqual(launch.returncode, 0, launch.stderr + launch.stdout)
            pid = parse_json_object(launch.stdout, {"pid"})["pid"]
            stack.callback(lambda: run_lgwf(["stop", "--pid", str(pid)], env=env, timeout=30))

            choices: list[tuple[str, str]] = []
            deadline = time.monotonic() + 180
            final_status: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                status = self.wait_status(pid=pid, work_dir=work_dir, env=env, timeout_seconds=20)
                final_status = status
                phase = str(status.get("phase") or "")
                if status.get("running") is False or phase in {"completed", "failed"}:
                    break

                request_id = self.request_id(status)
                request = self.read_human_request(work_dir=work_dir, request_id=request_id)
                kind = request.get("kind")
                if kind is None:
                    kind = "human_choice" if request.get("options") else "human_approval"
                pending_action = status.get("pending_action")
                node_id = str(request.get("node_id") or status.get("current_node") or "")
                if not node_id and isinstance(pending_action, dict):
                    node_id = str(
                        pending_action.get("node_id")
                        or pending_action.get("current_node")
                        or pending_action.get("node")
                        or pending_action.get("child_node_id")
                        or ""
                    )

                if kind == "human_approval":
                    self.submit_approval(work_dir=work_dir, env=env, request_id=request_id, value={"post_fix_target": target})
                    self.wait_for_request_change(
                        pid=pid,
                        work_dir=work_dir,
                        env=env,
                        previous_request_id=request_id,
                    )
                    continue

                if kind == "human_choice" or (kind == "human_review" and request.get("options")):
                    self.assertIsInstance(request.get("option_labels"), dict)
                    if not choices:
                        route = "auto"
                    else:
                        route = "skip"
                    choices.append((node_id, route))
                    self.submit_choice(work_dir=work_dir, env=env, request_id=request_id, route=route)
                    self.wait_for_request_change(
                        pid=pid,
                        work_dir=work_dir,
                        env=env,
                        previous_request_id=request_id,
                    )
                    continue

                raise AssertionError(f"unexpected human request kind={kind!r}: {request}")
            else:
                log_tail = log_file.read_text(encoding="utf-8", errors="replace")[-8000:] if log_file.exists() else ""
                raise AssertionError(f"workflow did not finish; last={final_status}; log tail:\n{log_tail}")

            self.assertIsNotNone(final_status)
            self.assertEqual(final_status.get("phase"), "completed", final_status)
            self.assertEqual([route for _, route in choices], ["auto", "skip", "skip"], choices)

            decisions = read_json(work_dir / ".lgwf" / "post_fix_decisions.json")
            self.assertTrue(decisions["auto_enabled"])
            decision_routes = {item["stage_id"]: item["route"] for item in decisions["stages"]}
            self.assertEqual(decision_routes["prompt_fix"], "run")
            self.assertEqual(decision_routes["prompt_upgrade"], "run")
            self.assertEqual(decision_routes["e2e_generate"], "run")
            self.assertEqual(decision_routes["script_flow_e2e"], "run")
            self.assertEqual(decision_routes["runtime_fake_e2e"], "run")
            self.assertEqual(decision_routes["real_positive_e2e"], "skip")
            self.assertEqual(decision_routes["wf_fix_positive_e2e"], "skip")

            trace_path = work_dir / ".lgwf-test" / "run_workflow_trace.jsonl"
            traces = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([item["node_id"] for item in traces], ["prompt_fix", "prompt_upgrade", "e2e_generate"])
            e2e_child = next(item for item in traces if item["node_id"] == "e2e_generate")
            self.assertEqual(e2e_child["input"]["test_types"], ["script_flow", "runtime_fake"])
            self.assertNotIn("real_positive", e2e_child["input"]["test_types"])

            summary = read_json(work_dir / ".lgwf" / "post_fix_summary.json")
            self.assertEqual(summary["target"], target)
            self.assertTrue((work_dir / "reports" / "wf-post-fix" / "report.md").is_file())


if __name__ == "__main__":
    unittest.main()
