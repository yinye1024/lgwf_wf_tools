from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ROOT = PACKAGE_ROOT / "wf"
FACADE_ROOT = PACKAGE_ROOT.parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[5]


def find_lgwf() -> Path:
    explicit = os.environ.get("LGWF_CLIENT_ASSIST_LGWF_PY")
    if explicit:
        return Path(explicit)
    return FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


LGWF = find_lgwf()


def run_lgwf(args: list[str], *, env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(LGWF), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
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
    raise AssertionError(f"stdout did not contain a JSON object{expected}:\n{text}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def runtime_temp_dir(stack: ExitStack, prefix: str) -> str:
    if os.environ.get("LGWF_PLAN_RUNTIME_E2E_KEEP_WORKDIR") == "1":
        return tempfile.mkdtemp(prefix=prefix)
    return stack.enter_context(tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True))


def write_prompt_file_mode_patch(patch_dir: Path) -> None:
    patch_dir.mkdir(parents=True, exist_ok=True)
    (patch_dir / "sitecustomize.py").write_text(
        r'''
from __future__ import annotations

import os
import pathlib
import uuid


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
            prompt_dir = work_dir / ".lgwf" / "fake_codex_prompts"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = prompt_dir / f"{uuid.uuid4().hex}.txt"
            prompt_path.write_text(command[-1], encoding="utf-8")
            command = [*command[:-1], "--prompt-file", str(prompt_path)]
        return _original_resolve(self, command)

    process_execution.CommandResolver.resolve = _resolve_with_prompt_file
'''.lstrip(),
        encoding="utf-8",
    )


def write_fake_codex(fake_bin: Path) -> None:
    # Fake Codex 契约：输入为 --prompt-file 指向的 LGWF handoff prompt；脚本读取其中的 Main prompt file，
    # 按 prompt 路径映射到固定 node 输出，不依赖调用顺序或重试次数。
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_py = fake_bin / "fake_codex.py"
    fake_py.write_text(
        r'''
from __future__ import annotations

import json
import os
import pathlib
import sys


def write_json(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def plan() -> dict:
    task_defs = [
        ("task-1", "collect_runtime_intent"),
        ("task-2", "design_step_documents"),
        ("task-3", "confirm_step_designs"),
        ("task-4", "finalize_step_designs"),
        ("task-5", "summarize_runtime_result"),
    ]
    tasks = []
    for index, (task_id, title) in enumerate(task_defs, start=1):
        tasks.append(
            {
                "task_id": task_id,
                "title": title,
                "scope_detail": {"files": [f"src/runtime_task_{index}.txt"]},
                "implementation_steps": [
                    f"准备 {task_id} 的输入契约",
                    f"写入 {task_id} 的可验收产物",
                ],
                "acceptance_seed": [f"{task_id} evidence"],
                "required_checks_hint": ["python -m unittest"],
            }
        )
    return {
        "summary": {
            "problem_statement": "启动真实 lgwf-plan workflow 并覆盖运行时主干。",
            "proposed_approach": "用 fake codex 产出确定性计划、验收和执行结果。",
            "workflow_flow": [task["title"] for task in tasks],
            "key_decisions": [],
            "alternatives_considered": [],
            "open_questions": [],
            "quality_bar": ["5 个 task 全部通过"],
        },
        "tasks": tasks,
    }


def acceptance(plan_data: dict) -> dict:
    items = []
    for task in plan_data["tasks"]:
        items.append(
            {
                "task_id": task["task_id"],
                "criteria": [f"{task['task_id']} 完成"],
                "required_checks": ["python -m unittest"],
                "review_focus": ["只检查当前 task"],
                "out_of_scope": ["未声明文件"],
                "plan_validation_map": [
                    {
                        "plan_step_index": idx,
                        "plan_step": step,
                        "expected_evidence": f"{task['task_id']} step {idx} evidence",
                        "validation": "检查 fake codex 生成的结构化结果",
                    }
                    for idx, step in enumerate(task["implementation_steps"])
                ],
            }
        )
    return {"tasks": items}


def pass_result(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "verdict": "pass",
        "pass": True,
        "accepted": True,
        "evidence": [f"{task_id} runtime evidence"],
        "criteria_results": [{"criteria": f"{task_id} 完成", "passed": True}],
        "required_check_results": [{"check": "python -m unittest", "passed": True}],
        "negative_check_results": [{"check": "未声明文件", "passed": True}],
        "risk_check_results": [{"risk": "范围漂移", "passed": True}],
        "plan_validation_results": [{"plan_step_index": 0, "passed": True}, {"plan_step_index": 1, "passed": True}],
        "scope_compliance": {"within_scope": True, "issues": []},
        "required_follow_up": [],
    }


def manual_approval_result(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "verdict": "fail",
        "pass": False,
        "accepted": False,
        "blocking_reason": "manual_approval_required",
        "evidence": [
            {"evidence_id": "step_design_confirmation_record_absent", "target": ".lgwf/step_design_confirmation_record.json"},
            {"evidence_id": "step_designs_json_absent", "target": ".lgwf/step_designs.json"},
        ],
        "criteria_results": [{"criteria": "步骤设计需要人工确认", "passed": False}],
        "required_check_results": [{"check_id": "check_step_design_confirmation", "passed": False}],
        "negative_check_results": [{"check": "不能把未确认设计当作已确认输入", "passed": True}],
        "risk_check_results": [{"risk": "跳过业务门禁", "passed": False}],
        "plan_validation_results": [{"plan_step_index": 0, "passed": False}],
        "scope_compliance": {"within_scope": True, "issues": []},
        "required_follow_up": [
            {
                "type": "approval",
                "title": "确认步骤设计",
                "approval_artifact": ".lgwf/step_design_confirmation_record.json",
                "confirmed_artifact": ".lgwf/step_designs.json",
            }
        ],
    }


NODE_OUTPUTS = {
    "01_generate_plan/02_generate_plan_proposal/agents/reason.md": "plan_reason",
    "01_generate_plan/02_generate_plan_proposal/agents/act.md": "plan_act",
    "01_generate_plan/02_generate_plan_proposal/agents/observe.md": "plan_observe",
    "02_generate_acceptance/00_generate_acceptance_proposal/agents/reason.md": "acceptance_reason",
    "02_generate_acceptance/00_generate_acceptance_proposal/agents/act.md": "acceptance_act",
    "02_generate_acceptance/00_generate_acceptance_proposal/agents/observe.md": "acceptance_observe",
    "04_execute_react_loop/01_implement_task/agents/reason.md": "task_reason",
    "04_execute_react_loop/01_implement_task/agents/act.md": "task_act",
    "04_execute_react_loop/01_implement_task/agents/observe.md": "task_observe",
}


def extract_handoff_prompt(argv: list[str]) -> str:
    for index, arg in enumerate(argv[1:], start=1):
        if arg == "--prompt-file" and index + 1 < len(argv):
            return pathlib.Path(argv[index + 1]).read_text(encoding="utf-8")
        if arg.startswith("--prompt-file="):
            return pathlib.Path(arg.split("=", 1)[1]).read_text(encoding="utf-8")
        if arg.startswith("# LGWF Codex Handoff"):
            return arg
        candidate = pathlib.Path(arg)
        if candidate.exists() and candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            if "# LGWF Codex Handoff" in text:
                return text
    stdin_text = sys.stdin.read()
    if "# LGWF Codex Handoff" in stdin_text:
        return stdin_text
    return ""


def extract_main_prompt_path(prompt: str) -> str:
    lines = prompt.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() == "Main prompt file:":
            return lines[index + 1].strip().replace("\\", "/")
    return ""


def resolve_node_key(prompt: str) -> str:
    main_prompt_path = extract_main_prompt_path(prompt)
    for suffix, key in NODE_OUTPUTS.items():
        if suffix in main_prompt_path:
            return key
    raise SystemExit(f"fake codex did not recognize main prompt path: {main_prompt_path or '<missing>'}")


def main() -> int:
    prompt = extract_handoff_prompt(sys.argv)
    root = pathlib.Path(os.environ.get("LGWF_FAKE_CODEX_WORK_DIR") or pathlib.Path.cwd())
    lgwf = root / ".lgwf"
    node_key = resolve_node_key(prompt)
    stdout_payload = {"token_usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}

    if node_key == "plan_reason":
        write_text(lgwf / "react_task_plan_reason.md", "runtime e2e plan reason\n")
    elif node_key == "plan_act":
        stdout_payload = plan()
        write_json(lgwf / "react_task_plan_proposal.json", stdout_payload)
    elif node_key == "plan_observe":
        stdout_payload = {
                "verdict": "pass",
                "ready_for_acceptance_generation": True,
                "issues": [],
                "required_changes": [],
            }
    elif node_key == "acceptance_reason":
        stdout_payload = {
            "task_alignment_summary": [{"task_id": "task-1", "summary": "runtime e2e acceptance reason"}],
            "acceptance_goal_analysis": [],
            "evidence_analysis": [],
            "required_checks_analysis": [],
            "negative_checks_analysis": [],
            "risk_checks_analysis": [],
            "pass_fail_judgement": [],
            "scope_boundaries": {"in_scope": [], "out_of_scope": []},
            "open_questions": [],
        }
        write_json(lgwf / "react_acceptance_reason.json", stdout_payload)
    elif node_key == "acceptance_act":
        plan_data = json.loads((lgwf / "react_task_plan_proposal.json").read_text(encoding="utf-8-sig"))
        reason_data = json.loads((lgwf / "react_acceptance_reason.json").read_text(encoding="utf-8-sig"))
        if not reason_data.get("task_alignment_summary"):
            raise SystemExit("managed acceptance reason JSON was not available to acceptance act")
        stdout_payload = acceptance(plan_data)
        write_json(lgwf / "react_acceptance_proposal.json", stdout_payload)
    elif node_key == "acceptance_observe":
        stdout_payload = {
                "verdict": "pass",
                "acceptance_is_executable": True,
                "plan_validation_map_complete": True,
                "ready_for_confirmation": True,
                "issues": [],
                "required_changes": [],
            }
    elif node_key == "task_reason":
        write_text(lgwf / "react_task_implementation_reason.md", "runtime e2e implementation reason\n")
    elif node_key == "task_act":
        context = json.loads((lgwf / "react_task_context.json").read_text(encoding="utf-8-sig"))
        task_id = context["task"]["task_id"]
        stdout_payload = {"task_id": task_id, "changed_files": [f"src/{task_id}.txt"]}
    elif node_key == "task_observe":
        context = json.loads((lgwf / "react_task_context.json").read_text(encoding="utf-8-sig"))
        task_id = context["task"]["task_id"]
        if task_id == "task-3":
            stdout_payload = manual_approval_result(task_id)
        else:
            stdout_payload = pass_result(task_id)

    print(json.dumps(stdout_payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip(),
        encoding="utf-8",
    )
    for name in ("codex.cmd", "codex.bat"):
        (fake_bin / name).write_text(f'@echo off\r\npython "%~dp0fake_codex.py" %*\r\n', encoding="utf-8")


def fake_handoff(main_prompt_path: str) -> str:
    return "\n".join(
        [
            "# LGWF Codex Handoff",
            "",
            "Main prompt file:",
            main_prompt_path,
            "",
        ]
    )


class FakeCodexContractTest(unittest.TestCase):
    def test_fake_codex_routes_by_main_prompt_path_without_call_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lgwf-plan-fake-codex-contract-") as temp:
            temp_root = Path(temp)
            fake_bin = temp_root / "fake-bin"
            work_dir = temp_root / "work"
            lgwf = work_dir / ".lgwf"
            lgwf.mkdir(parents=True)
            write_fake_codex(fake_bin)
            self.assertFalse((fake_bin / "node_modules").exists())

            env = dict(os.environ)
            env["LGWF_FAKE_CODEX_WORK_DIR"] = str(work_dir)
            script = fake_bin / "fake_codex.py"
            acceptance_prompt = temp_root / "acceptance_observe_prompt.txt"
            plan_prompt = temp_root / "plan_act_prompt.txt"
            acceptance_prompt.write_text(
                fake_handoff("D:/snapshot/02_generate_acceptance/00_generate_acceptance_proposal/agents/observe.md"),
                encoding="utf-8",
            )
            plan_prompt.write_text(
                fake_handoff("D:/snapshot/01_generate_plan/02_generate_plan_proposal/agents/act.md"),
                encoding="utf-8",
            )

            first = subprocess.run(
                [
                    "python",
                    str(script),
                    "exec",
                    "--prompt-file",
                    str(acceptance_prompt),
                ],
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)["verdict"], "pass")
            self.assertFalse((lgwf / "react_acceptance_observe.json").exists())
            self.assertFalse((lgwf / "fake_codex_calls.json").exists())

            second = subprocess.run(
                [
                    "python",
                    str(script),
                    "exec",
                    "--prompt-file",
                    str(plan_prompt),
                ],
                env=env,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(len(json.loads(second.stdout)["tasks"]), 5)
            self.assertEqual(len(read_json(lgwf / "react_task_plan_proposal.json")["tasks"]), 5)


@unittest.skipUnless(LGWF.exists(), f"LGWF facade not found: {LGWF}")
class LgwfPlanRuntimeEndToEndTest(unittest.TestCase):
    def test_runtime_workflow_e2e_starts_lgwf_plan_and_completes_five_tasks(self) -> None:
        with ExitStack() as stack:
            temp = runtime_temp_dir(stack, "lgwf-plan-runtime-e2e-")
            temp_root = Path(temp)
            fake_bin = temp_root / "fake-bin"
            patch_dir = temp_root / "pythonpath"
            work_dir = temp_root / "work"
            log_file = temp_root / "workflow.log"
            write_fake_codex(fake_bin)
            write_prompt_file_mode_patch(patch_dir)
            work_dir.mkdir()

            env = dict(os.environ)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            env["LGWF_FAKE_CODEX_WORK_DIR"] = str(work_dir)
            env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
            env["PYTHONPATH"] = str(patch_dir) + os.pathsep + env.get("PYTHONPATH", "")

            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(ROOT / "workflow.lgwf"),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    json.dumps({"case": "runtime-e2e"}, ensure_ascii=False),
                    "--background",
                    "--log-file",
                    str(log_file),
                    "--rerun-existing",
                ],
                env=env,
            )
            self.assertEqual(launch.returncode, 0, launch.stderr + launch.stdout)
            metadata = parse_json_object(launch.stdout, {"pid"})
            pid = metadata["pid"]

            stack.callback(lambda: run_lgwf(["stop", "--pid", str(pid)], env=env, timeout=30))

            seen_approval_contexts: list[Any] = []
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                status_result = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], env=env, timeout=30)
                self.assertEqual(status_result.returncode, 0, status_result.stderr + status_result.stdout)
                status = parse_json_object(status_result.stdout, {"running"})
                if status.get("running") is False or status.get("phase") == "completed":
                    break

                request_id = status.get("human_request_id")
                pending = status.get("pending_human_requests") or []
                if request_id is None and pending:
                    request_id = pending[0].get("request_id")
                if request_id:
                    request = run_lgwf(
                        ["approval", "get", "--work-dir", str(work_dir), "--request-id", str(request_id)],
                        env=env,
                        timeout=30,
                    )
                    self.assertEqual(request.returncode, 0, request.stderr + request.stdout)
                    approval_request = parse_json_object(request.stdout, {"request_id"})
                    context = approval_request.get("context")
                    prompt = str(approval_request.get("prompt") or "")
                    seen_approval_contexts.append(context)
                    if isinstance(context, dict) and context.get("tasks"):
                        value = {"approval": "approve", "comment": "runtime e2e approved"}
                    elif (
                        isinstance(context, dict)
                        and any(
                            isinstance(item, dict) and (item.get("approval_artifact") or item.get("confirmed_artifact"))
                            for item in context.get("required_follow_up", [])
                        )
                    ):
                        for item in context.get("required_follow_up", []):
                            if not isinstance(item, dict):
                                continue
                            for key in ("approval_artifact", "confirmed_artifact"):
                                artifact = item.get(key)
                                if isinstance(artifact, str) and artifact:
                                    write_json(work_dir / artifact, {"decision": "approve", "source": "runtime e2e fixture"})
                        value = {
                            "action": "accept",
                            "comment": "runtime e2e accepted after business artifacts were written",
                        }
                    elif "业务门禁" in prompt or '"action"' in prompt or "continue|accept|skip|stop" in prompt or (
                        isinstance(context, dict)
                        and (context.get("route") == "requires_user_approval" or context.get("blocking_reason") == "manual_approval_required")
                    ):
                        value = {
                            "action": "continue",
                            "comment": "runtime e2e continue manual gate",
                        }
                    elif "任务输入确认" in prompt or "react_task_request.json" in prompt:
                        value = {
                            "objective": "启动真实 lgwf-plan 工作流的 E2E 测试",
                            "target_type": "modify_artifact",
                            "request": "覆盖真实 runtime 主干，计划必须拆分为至少 5 个 task",
                            "analysis_target_dirs": ["."],
                            "analysis_target_files": [],
                        }
                    else:
                        value = context if isinstance(context, dict) else {"approval": "approve"}
                    submit = run_lgwf(
                        [
                            "approval",
                            "submit",
                            "--work-dir",
                            str(work_dir),
                            "--request-id",
                            str(request_id),
                            "--decision",
                            "approve",
                            "--value-json",
                            json.dumps(value, ensure_ascii=False),
                            "--comment",
                            "runtime e2e auto approve",
                        ],
                        env=env,
                        timeout=30,
                    )
                    self.assertEqual(submit.returncode, 0, submit.stderr + submit.stdout)
                else:
                    time.sleep(0.5)
            else:
                self.fail(f"workflow did not finish before timeout; log:\n{log_file.read_text(encoding='utf-8', errors='replace') if log_file.exists() else ''}")

            self.assertTrue(
                (work_dir / ".lgwf" / "react_task_plan.json").exists(),
                log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else "missing workflow log",
            )
            self.assertTrue(
                (work_dir / "reports" / "react-task" / "react_task_report.json").exists(),
                log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else "missing workflow log",
            )
            plan = read_json(work_dir / ".lgwf" / "react_task_plan.json")
            acceptance = read_json(work_dir / ".lgwf" / "react_acceptance_plan.json")
            report = read_json(work_dir / "reports" / "react-task" / "react_task_report.json")

            self.assertEqual(len(plan["tasks"]), 5)
            self.assertEqual(len(acceptance["tasks"]), 5)
            self.assertTrue(all(task["status"] == "passed" for task in plan["tasks"]))
            self.assertEqual([task["title"] for task in plan["tasks"][1:4]], ["design_step_documents", "confirm_step_designs", "finalize_step_designs"])
            self.assertEqual(plan["tasks"][2]["attempts"], 1)
            self.assertEqual(plan["tasks"][2]["max_attempt_decision"]["action"], "accept")
            self.assertIsNone(report["current_task_id"])
            self.assertEqual(report["history_count"], 6)
            self.assertGreaterEqual(len(seen_approval_contexts), 2)
            self.assertTrue((work_dir / ".lgwf" / "workflow" / "workflow.lgwf").exists())
            self.assertTrue(any((work_dir / ".lgwf" / "codex").glob("**/prompt.txt")))
            self.assertTrue((work_dir / ".lgwf" / "react_acceptance_reason.json").exists())
            self.assertFalse((work_dir / ".lgwf" / "react_acceptance_reason.md").exists())
            acceptance_reason = read_json(work_dir / ".lgwf" / "react_acceptance_reason.json")
            self.assertTrue(acceptance_reason["task_alignment_summary"])

    def test_runtime_workflow_e2e_covers_reject_branch(self) -> None:
        with ExitStack() as stack:
            temp = runtime_temp_dir(stack, "lgwf-plan-runtime-reject-")
            temp_root = Path(temp)
            fake_bin = temp_root / "fake-bin"
            patch_dir = temp_root / "pythonpath"
            work_dir = temp_root / "work"
            log_file = temp_root / "workflow.log"
            write_fake_codex(fake_bin)
            write_prompt_file_mode_patch(patch_dir)
            work_dir.mkdir()
            env = dict(os.environ)
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            env["LGWF_FAKE_CODEX_WORK_DIR"] = str(work_dir)
            env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
            env["PYTHONPATH"] = str(patch_dir) + os.pathsep + env.get("PYTHONPATH", "")

            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(ROOT / "workflow.lgwf"),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    json.dumps({"case": "runtime-reject"}, ensure_ascii=False),
                    "--background",
                    "--log-file",
                    str(log_file),
                    "--rerun-existing",
                ],
                env=env,
            )
            self.assertEqual(launch.returncode, 0, launch.stderr + launch.stdout)
            pid = parse_json_object(launch.stdout, {"pid"})["pid"]
            stack.callback(lambda: run_lgwf(["stop", "--pid", str(pid)], env=env, timeout=30))

            deadline = time.monotonic() + 60
            rejected = False
            while time.monotonic() < deadline:
                status_result = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], env=env, timeout=30)
                self.assertEqual(status_result.returncode, 0, status_result.stderr + status_result.stdout)
                status = parse_json_object(status_result.stdout, {"running"})
                request_id = status.get("human_request_id")
                pending = status.get("pending_human_requests") or []
                if request_id is None and pending:
                    request_id = pending[0].get("request_id")
                if request_id:
                    submit = run_lgwf(
                        [
                            "approval",
                            "submit",
                            "--work-dir",
                            str(work_dir),
                            "--request-id",
                            str(request_id),
                            "--decision",
                            "reject",
                            "--comment",
                            "runtime e2e reject branch",
                        ],
                        env=env,
                        timeout=30,
                    )
                    self.assertEqual(submit.returncode, 0, submit.stderr + submit.stdout)
                    rejected = True
                    break
                time.sleep(0.5)
            self.assertTrue(rejected, "workflow did not reach initial approval")

            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                status_result = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], env=env, timeout=30)
                status = parse_json_object(status_result.stdout, {"running"})
                if status.get("running") is False:
                    self.assertIn(status.get("phase"), {"failed", "completed"})
                    break
                time.sleep(0.5)
            else:
                self.fail("reject branch workflow did not stop")


if __name__ == "__main__":
    unittest.main()
