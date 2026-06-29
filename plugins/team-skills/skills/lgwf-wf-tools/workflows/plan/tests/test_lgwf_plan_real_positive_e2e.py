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
ROOT = PACKAGE_ROOT / "wf"
FACADE_ROOT = PACKAGE_ROOT.parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[5]


def find_lgwf() -> Path:
    explicit = os.environ.get("LGWF_CLIENT_ASSIST_LGWF_PY")
    if explicit:
        return Path(explicit)
    return FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


LGWF = find_lgwf()
ENABLE_REAL_E2E = os.environ.get("LGWF_PLAN_REAL_CODEX_E2E") == "1"


def real_e2e_timeout_seconds() -> int:
    raw = os.environ.get("LGWF_PLAN_REAL_CODEX_E2E_TIMEOUT_SECONDS", "5400")
    try:
        value = int(raw)
    except ValueError as exc:
        raise AssertionError("LGWF_PLAN_REAL_CODEX_E2E_TIMEOUT_SECONDS must be an integer") from exc
    if value <= 0:
        raise AssertionError("LGWF_PLAN_REAL_CODEX_E2E_TIMEOUT_SECONDS must be positive")
    return value


def run_lgwf(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", str(LGWF), *args],
        cwd=REPO_ROOT,
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def preserve_artifacts(temp_root: Path, reason: str) -> Path:
    target_root = PACKAGE_ROOT / "tests" / ".tmp"
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = target_root / f"real-positive-{stamp}-{reason}"
    shutil.copytree(temp_root, target, dirs_exist_ok=True)
    return target


def create_task_summary_fixture(work_dir: Path) -> None:
    root = work_dir / "task_summary_tool"
    write_text(
        root / "README.md",
        "# task_summary_tool\n\n一个待实现的任务清单摘要工具。\n",
    )
    write_text(root / "task_summary" / "__init__.py", "")
    write_text(
        root / "tests" / "test_task_summary.py",
        """import unittest\n\n\nclass PlaceholderTest(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n""",
    )


def positive_task_request() -> dict[str, Any]:
    return {
        "objective": "为临时 task_summary_tool 项目实现任务清单摘要工具",
        "target_type": "modify_artifact",
        "request": (
            "请先理解现有 task_summary_tool 目录，然后把任务拆分为正好 3 个 task，"
            "按 lgwf-plan 正向流程实现。目标：输入 JSON 文件包含 tasks 列表，每个 task 有 "
            "title、status、owner；工具需要读取 JSON，统计总数、按 status 汇总、按 owner 汇总，"
            "并输出 Markdown 摘要。必须提供 task_summary.summarize_tasks(tasks) 和 "
            "task_summary.render_markdown(summary) 两个可导入 API；summary 至少包含 total、"
            "status_counts、owner_counts。请补充单元测试和 README 用法。"
            "每个 task 都必须能产出可通过的完成结果，不要设计“先写失败测试但不实现”的中间 task。"
        ),
        "constraints": [
            "计划必须拆分为正好 3 个 task",
            "只修改 task_summary_tool 目录",
            "每个 task 的验收都必须是正向可通过验收，不要把故意失败的测试作为最终验收",
            "必须提供 summarize_tasks(tasks) 和 render_markdown(summary) API",
            "最终必须能在 task_summary_tool 下运行 python -m unittest discover tests",
        ],
        "analysis_target_dirs": ["task_summary_tool"],
        "analysis_target_files": [],
    }


def approve_value_for_request(approval_request: dict[str, Any], work_dir: Path) -> dict[str, Any]:
    prompt = str(approval_request.get("prompt") or "")
    context = approval_request.get("context")
    if "react_task_request.json" in prompt or "任务输入确认" in prompt:
        create_task_summary_fixture(work_dir)
        return positive_task_request()
    if isinstance(context, dict) and context.get("tasks"):
        return {"approval": "approve", "comment": "real positive E2E approved"}
    return context if isinstance(context, dict) else {"approval": "approve"}


def write_black_box_tests(project: Path) -> None:
    write_text(
        project / "tests" / "test_lgwf_plan_black_box.py",
        """import unittest

from task_summary import render_markdown, summarize_tasks


class LgwfPlanBlackBoxTest(unittest.TestCase):
    def test_summarizes_status_owner_and_markdown(self):
        tasks = [
            {"title": "Design", "status": "done", "owner": "alice"},
            {"title": "Build", "status": "todo", "owner": "bob"},
            {"title": "Review", "status": "done", "owner": "alice"},
        ]
        summary = summarize_tasks(tasks)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["status_counts"]["done"], 2)
        self.assertEqual(summary["status_counts"]["todo"], 1)
        self.assertEqual(summary["owner_counts"]["alice"], 2)
        markdown = render_markdown(summary)
        self.assertIn("done", markdown)
        self.assertIn("alice", markdown)
        self.assertIn("3", markdown)


if __name__ == "__main__":
    unittest.main()
""",
    )


@unittest.skipUnless(
    ENABLE_REAL_E2E and LGWF.exists(),
    "set LGWF_PLAN_REAL_CODEX_E2E=1 to run the real Codex-backed lgwf-plan E2E test",
)
class LgwfPlanRealPositiveEndToEndTest(unittest.TestCase):
    def test_real_codex_positive_business_flow_completes_task_summary_tool(self) -> None:
        temp_root = Path(tempfile.mkdtemp(prefix="lgwf-plan-real-positive-"))
        work_dir = temp_root / "work"
        log_file = temp_root / "workflow.log"
        work_dir.mkdir()
        pid: int | None = None
        preserve = os.environ.get("LGWF_PLAN_REAL_CODEX_E2E_KEEP_WORKDIR") == "1"

        try:
            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(ROOT / "workflow.lgwf"),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    json.dumps({"scenario": "real-positive-task-summary-tool"}, ensure_ascii=False),
                    "--background",
                    "--log-file",
                    str(log_file),
                    "--rerun-existing",
                ],
                timeout=180,
            )
            self.assertEqual(launch.returncode, 0, launch.stderr + launch.stdout)
            metadata = parse_json_object(launch.stdout, {"pid"})
            pid = metadata["pid"]

            deadline = time.monotonic() + real_e2e_timeout_seconds()
            while time.monotonic() < deadline:
                status_result = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], timeout=60)
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
                        timeout=60,
                    )
                    self.assertEqual(request.returncode, 0, request.stderr + request.stdout)
                    approval_request = parse_json_object(request.stdout, {"request_id"})
                    value = approve_value_for_request(approval_request, work_dir)
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
                            "real positive E2E auto approval",
                        ],
                        timeout=60,
                    )
                    self.assertEqual(submit.returncode, 0, submit.stderr + submit.stdout)
                else:
                    time.sleep(5)
            else:
                log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
                preserved = preserve_artifacts(temp_root, "timeout")
                self.fail(f"workflow did not finish before timeout; preserved={preserved}; log:\n{log[-8000:]}")
        finally:
            if pid is not None:
                run_lgwf(["stop", "--pid", str(pid)], timeout=30)

        try:
            log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
            plan_path = work_dir / ".lgwf" / "react_task_plan.json"
            acceptance_path = work_dir / ".lgwf" / "react_acceptance_plan.json"
            report_path = work_dir / "reports" / "react-task" / "react_task_report.json"
            self.assertTrue(plan_path.exists(), log[-8000:])
            self.assertTrue(acceptance_path.exists(), log[-8000:])
            self.assertTrue(report_path.exists(), log[-8000:])

            plan = read_json(plan_path)
            acceptance = read_json(acceptance_path)
            report = read_json(report_path)
            tasks = plan.get("tasks", [])
            self.assertEqual(len(tasks), 3)
            self.assertEqual(len(acceptance.get("tasks", [])), len(tasks))
            self.assertTrue(all(task.get("status") == "passed" for task in tasks), tasks)
            self.assertIsNone(report.get("current_task_id"))
            self.assertEqual(report.get("history_count"), len(tasks))

            project = work_dir / "task_summary_tool"
            for relative in (
                "README.md",
                "task_summary/__init__.py",
                "tests/test_task_summary.py",
            ):
                self.assertTrue((project / relative).exists(), f"missing {relative}")
            self.assertTrue(
                any((project / "task_summary").glob("*.py")),
                "expected real Codex execution to create or update task_summary Python modules",
            )

            write_black_box_tests(project)
            project_tests = subprocess.run(
                ["python", "-m", "unittest", "discover", "tests"],
                cwd=project,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
            )
            self.assertEqual(project_tests.returncode, 0, project_tests.stdout + project_tests.stderr)
        except Exception:
            preserved = preserve_artifacts(temp_root, "failure")
            print(f"preserved real E2E artifacts at {preserved}")
            raise
        finally:
            if preserve:
                preserved = preserve_artifacts(temp_root, "kept")
                print(f"preserved real E2E artifacts at {preserved}")
            else:
                shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
