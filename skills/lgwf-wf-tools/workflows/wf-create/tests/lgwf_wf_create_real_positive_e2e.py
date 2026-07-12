from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = PACKAGE_ROOT.parents[1]
WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
VENDOR_ROOT = FACADE_ROOT / "vendor" / "lgwf-client-assist"
DOCS_SOURCE = FACADE_ROOT / "docs" / "LGWF_WF_MODULAR_DEVELOPMENT.md"
MODULE_CONTRACT_SOURCE = FACADE_ROOT / "workflows" / "01-share" / "module-contract.md"

WORKFLOW_NAME = "repo_context_pack"
TARGET_PACKAGE_ROOT = "skills/repo-context-pack"
RAW_INTENT = """我想创建一个 repo-context-pack 工作流。

这个工作流用于帮助 AI agent 在接手一个陌生仓库或某个模块目录之前，快速生成一份可阅读、可交接的上下文包。用户提供一个本地目录作为输入，目录可以是完整仓库，也可以是仓库中的某个模块。

工作流需要只读扫描这个目标目录，识别关键入口文件、模块目录、常见开发命令、测试入口、风险标记和推荐阅读顺序，然后生成一组上下文产物，帮助后续 agent 更快理解这个目标：它是什么、从哪里读起、有哪些命令、有哪些风险、修改前需要注意什么。

核心输出应该包括：
- 一份面向 agent 的主上下文报告。
- 一份 handoff 摘要，方便下一个 agent 接手。
- 一份模块地图，列出入口文件和重要目录。
- 一份命令清单，汇总从文档、脚本和配置中发现的常用命令。
- 一份风险清单，汇总 TODO、FIXME、manual、approval、risk 等风险候选。
- 一份推荐阅读顺序。
- 一份结构化 summary，记录扫描参数、产物索引和是否发生截断。

这个工作流的第一版重点是确定性、只读和可交接：扫描和渲染应由 Python 脚本完成，不依赖 Codex prompt 直接理解整个仓库；不得修改被扫描目录源码，不修复目标仓库问题，不执行 Git 写操作，不发布、不部署、不注册到 facade registry。

用户可以指定扫描用途，例如 onboarding、modification、review、workflow-authoring 或 handoff；也可以指定扫描深度和最大文件数。对于大型目录，工作流应该有扫描上限，并在报告中明确标记截断状态。

生成的上下文包可以写入用户指定的输出目录；如果用户没有指定，则写入目标目录下的本地 context-packs 输出位置。工作流自身的运行状态必须与目标源码分离，不应把运行缓存写进被分析源码目录。"""
REPORT_RELATIVE = Path("reports") / "create-workflow" / "create_result_report.md"
APPROVAL_COMMENT = "real positive e2e auto approve"
MONITOR_POLL_INTERVAL_SECONDS = 30


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_completed(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int = 240,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    write_text(stdout_path, completed.stdout)
    write_text(stderr_path, completed.stderr)
    return completed


def parse_json_text(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def contains_text(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(contains_text(item, needle) for item in value)
    if isinstance(value, str):
        return needle in value.lower()
    return False


def status_indicates_waiting_human(status_payload: Any, raw_text: str) -> bool:
    return contains_text(status_payload, "waiting_human") or "waiting_human" in raw_text.lower()


def request_id_from_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    for key in ("request_id", "id"):
        value = str(item.get(key, "")).strip()
        if value:
            return value
    return ""


def request_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("request"), dict):
        return payload["request"]
    if isinstance(payload, dict):
        return payload
    return {}


def list_of_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return []


def allows_simple_approve(payload: Any, request_id: str) -> bool:
    request = request_payload(payload)
    if not request:
        return False
    embedded_id = str(request.get("request_id") or request.get("id") or "").strip()
    if embedded_id and embedded_id != request_id:
        return False

    approve_options = set()
    for key in ("allowed_decisions", "allowed_actions", "decisions", "options"):
        approve_options.update(list_of_strings(request.get(key)))

    can_approve = request.get("can_approve")
    supports_approve = request.get("supports_approve")
    has_approve_signal = "approve" in approve_options or can_approve is True or supports_approve is True
    if not has_approve_signal:
        return False

    for key in ("requires_value_json", "needs_value_json", "value_required", "requires_value"):
        if request.get(key) is True:
            return False
    if request.get("value_schema") or request.get("value_json_schema"):
        return False

    request_kind = str(
        request.get("kind") or request.get("request_kind") or request.get("request_type") or ""
    ).strip().lower()
    if request_kind and not any(token in request_kind for token in ("approval", "review", "choice")):
        return False
    return True


def sanitize_request_id(request_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in request_id)
    return safe or "unknown"


def kill_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def prepare_temp_workspace(temp_root: Path) -> dict[str, Path]:
    (temp_root / ".git").mkdir(parents=True, exist_ok=True)
    work_dir = temp_root / "work"
    artifacts_dir = temp_root / "artifacts"
    fixtures_dir = temp_root / "fixtures"
    copied_facade_root = temp_root / "skills" / "lgwf-wf-tools"
    copied_vendor_root = copied_facade_root / "vendor" / "lgwf-client-assist"
    copied_vendor_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(VENDOR_ROOT, copied_vendor_root)

    docs_target = copied_facade_root / "docs"
    docs_target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DOCS_SOURCE, docs_target / "LGWF_WF_MODULAR_DEVELOPMENT.md")

    share_target = copied_facade_root / "workflows" / "01-share"
    share_target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MODULE_CONTRACT_SOURCE, share_target / "module-contract.md")

    work_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    return {
        "work_dir": work_dir,
        "artifacts_dir": artifacts_dir,
        "fixtures_dir": fixtures_dir,
        "lgwf_py": copied_vendor_root / "scripts" / "lgwf.py",
    }


def real_positive_fixture() -> dict[str, Any]:
    return {
        "raw_intent": RAW_INTENT,
        "target_package_hint": (
            f"workflow_name={WORKFLOW_NAME}; "
            f"target_package_root={TARGET_PACKAGE_ROOT}; "
            "package_profile=internal_workflow_package"
        ),
    }


def capture_status(
    lgwf_py: Path,
    *,
    work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
    label: str,
    pid: int | None = None,
) -> tuple[subprocess.CompletedProcess[str], Any | None]:
    stdout_path = artifacts_dir / f"wf_create_status_{label}.stdout.txt"
    stderr_path = artifacts_dir / f"wf_create_status_{label}.stderr.txt"
    args = [sys.executable, str(lgwf_py), "status", "--work-dir", str(work_dir)]
    if pid is not None:
        args.extend(["--pid", str(pid)])
    completed = run_completed(
        args,
        cwd=temp_root,
        env=env,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout_seconds=120,
    )
    return completed, parse_json_text(completed.stdout)


def capture_codex_token_status(
    lgwf_py: Path,
    *,
    work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
    label: str,
) -> tuple[subprocess.CompletedProcess[str], Any | None]:
    stdout_path = artifacts_dir / f"wf_create_codex_token_status_{label}.stdout.txt"
    stderr_path = artifacts_dir / f"wf_create_codex_token_status_{label}.stderr.txt"
    completed = run_completed(
        [sys.executable, str(lgwf_py), "codex", "token-status", "--work-dir", str(work_dir)],
        cwd=temp_root,
        env=env,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout_seconds=120,
    )
    return completed, parse_json_text(completed.stdout)


def empty_approval_result() -> dict[str, Any]:
    return {"request_ids": [], "attempted_request_ids": [], "request_payload_paths": []}


def merge_approval_result(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in ("request_ids", "attempted_request_ids", "request_payload_paths"):
        seen = set(str(item) for item in target.get(key, []))
        merged = list(target.get(key, []))
        for item in source.get(key, []):
            item_text = str(item)
            if item_text and item_text not in seen:
                merged.append(item)
                seen.add(item_text)
        target[key] = merged


# auto approval fallback 固定遵循 approval list -> approval get -> approval submit。
def collect_pending_approvals(
    lgwf_py: Path,
    *,
    work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
    attempt_submit: bool,
) -> dict[str, Any]:
    list_completed = run_completed(
        [sys.executable, str(lgwf_py), "approval", "list", "--work-dir", str(work_dir)],
        cwd=temp_root,
        env=env,
        stdout_path=artifacts_dir / "pending_approval_list.stdout.txt",
        stderr_path=artifacts_dir / "pending_approval_list.stderr.txt",
        timeout_seconds=120,
    )
    parsed_list = parse_json_text(list_completed.stdout)
    requests = []
    if isinstance(parsed_list, dict) and isinstance(parsed_list.get("requests"), list):
        requests = parsed_list["requests"]

    attempted_request_ids: list[str] = []
    request_payload_paths: list[str] = []
    for item in requests:
        request_id = request_id_from_item(item)
        if not request_id:
            continue
        safe_id = sanitize_request_id(request_id)
        get_completed = run_completed(
            [
                sys.executable,
                str(lgwf_py),
                "approval",
                "get",
                "--work-dir",
                str(work_dir),
                "--request-id",
                request_id,
            ],
            cwd=temp_root,
            env=env,
            stdout_path=artifacts_dir / f"pending_approval_{safe_id}.stdout.txt",
            stderr_path=artifacts_dir / f"pending_approval_{safe_id}.stderr.txt",
            timeout_seconds=120,
        )
        payload_path = artifacts_dir / f"pending_approval_{safe_id}.json"
        write_text(payload_path, get_completed.stdout)
        request_payload_paths.append(str(payload_path))
        payload = parse_json_text(get_completed.stdout)
        if not attempt_submit or not allows_simple_approve(payload, request_id):
            continue
        submit_completed = run_completed(
            [
                sys.executable,
                str(lgwf_py),
                "approval",
                "submit",
                "--work-dir",
                str(work_dir),
                "--request-id",
                request_id,
                "--decision",
                "approve",
                "--comment",
                APPROVAL_COMMENT,
            ],
            cwd=temp_root,
            env=env,
            stdout_path=artifacts_dir / f"pending_approval_{safe_id}.submit.stdout.txt",
            stderr_path=artifacts_dir / f"pending_approval_{safe_id}.submit.stderr.txt",
            timeout_seconds=120,
        )
        if submit_completed.returncode == 0:
            attempted_request_ids.append(request_id)

    return {
        "request_ids": [request_id_from_item(item) for item in requests if request_id_from_item(item)],
        "attempted_request_ids": attempted_request_ids,
        "request_payload_paths": request_payload_paths,
    }


def wait_for_process_with_monitoring(
    process: subprocess.Popen[str],
    lgwf_py: Path,
    *,
    work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    approval_result = empty_approval_result()
    poll_index = 0

    while True:
        returncode = process.poll()
        if returncode is not None:
            return returncode, approval_result

        label = f"monitor_{poll_index:03d}"
        capture_status(
            lgwf_py,
            work_dir=work_dir,
            temp_root=temp_root,
            artifacts_dir=artifacts_dir,
            env=env,
            label=label,
            pid=process.pid,
        )
        capture_codex_token_status(
            lgwf_py,
            work_dir=work_dir,
            temp_root=temp_root,
            artifacts_dir=artifacts_dir,
            env=env,
            label=label,
        )
        poll_approval_result = collect_pending_approvals(
            lgwf_py,
            work_dir=work_dir,
            temp_root=temp_root,
            artifacts_dir=artifacts_dir,
            env=env,
            attempt_submit=True,
        )
        merge_approval_result(approval_result, poll_approval_result)

        try:
            return process.wait(timeout=MONITOR_POLL_INTERVAL_SECONDS), approval_result
        except subprocess.TimeoutExpired:
            poll_index += 1


class LgwfWfCreateRealPositiveE2ETest(unittest.TestCase):
    maxDiff = None

    def test_real_positive_repo_context_pack_flow(self) -> None:
        self.assertTrue(WORKFLOW_LGWF.is_file(), f"workflow missing: {WORKFLOW_LGWF}")
        self.assertIsNotNone(shutil.which("codex"), "PATH 中缺少 codex，无法运行真实 Codex 正向 E2E。")

        temp_root = Path(tempfile.mkdtemp(prefix="lgwf-wf-create-real-positive-"))
        success = False
        try:
            prepared = prepare_temp_workspace(temp_root)
            work_dir = prepared["work_dir"]
            artifacts_dir = prepared["artifacts_dir"]
            fixtures_dir = prepared["fixtures_dir"]
            lgwf_py = prepared["lgwf_py"]
            fixture_path = fixtures_dir / "real_positive_create_request.json"
            output_json_path = artifacts_dir / "wf_create_output.json"
            target_root = temp_root / TARGET_PACKAGE_ROOT
            write_json(fixture_path, real_positive_fixture())
            self.assertFalse(target_root.exists(), f"target package should start absent: {target_root}")

            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"

            audit_completed = run_completed(
                [sys.executable, str(lgwf_py), "audit", str(WORKFLOW_LGWF)],
                cwd=temp_root,
                env=env,
                stdout_path=artifacts_dir / "target_workflow_audit.stdout.txt",
                stderr_path=artifacts_dir / "target_workflow_audit.stderr.txt",
                timeout_seconds=240,
            )
            self.assertEqual(
                audit_completed.returncode,
                0,
                "\n".join(
                    [
                        "原始目标 workflow audit 未通过，真实正向入口已终止。",
                        f"temp_workspace={temp_root}",
                        f"stdout={artifacts_dir / 'target_workflow_audit.stdout.txt'}",
                        f"stderr={artifacts_dir / 'target_workflow_audit.stderr.txt'}",
                    ]
                ),
            )

            run_args = [
                sys.executable,
                str(lgwf_py),
                "run",
                "--workflow-lgwf",
                str(WORKFLOW_LGWF),
                "--work-dir",
                str(work_dir),
                "--input-json-file",
                str(fixture_path),
                "--auto-human",
                "--rerun-existing",
                "--output-json",
                str(output_json_path),
            ]

            stdout_handle = (artifacts_dir / "wf_create_run.stdout.txt").open("w", encoding="utf-8")
            stderr_handle = (artifacts_dir / "wf_create_run.stderr.txt").open("w", encoding="utf-8")
            try:
                process = subprocess.Popen(
                    run_args,
                    cwd=str(temp_root),
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                )
                approval_result = empty_approval_result()
                try:
                    returncode, approval_result = wait_for_process_with_monitoring(
                        process,
                        lgwf_py,
                        work_dir=work_dir,
                        temp_root=temp_root,
                        artifacts_dir=artifacts_dir,
                        env=env,
                    )
                except BaseException:
                    if process.poll() is None:
                        kill_process_tree(process)
                    raise
                final_status_completed, final_status_payload = capture_status(
                    lgwf_py,
                    work_dir=work_dir,
                    temp_root=temp_root,
                    artifacts_dir=artifacts_dir,
                    env=env,
                    label="final",
                    pid=process.pid,
                )
                capture_codex_token_status(
                    lgwf_py,
                    work_dir=work_dir,
                    temp_root=temp_root,
                    artifacts_dir=artifacts_dir,
                    env=env,
                    label="final",
                )
            finally:
                stdout_handle.close()
                stderr_handle.close()

            if returncode != 0 or status_indicates_waiting_human(
                final_status_payload,
                final_status_completed.stdout + "\n" + final_status_completed.stderr,
            ):
                final_approvals = collect_pending_approvals(
                    lgwf_py,
                    work_dir=work_dir,
                    temp_root=temp_root,
                    artifacts_dir=artifacts_dir,
                    env=env,
                    attempt_submit=False,
                )
                self.fail(
                    "\n".join(
                        [
                            "真实正向运行未成功完成，或仍停留在 waiting_human。",
                            f"returncode={returncode}",
                            f"monitor_poll_interval_seconds={MONITOR_POLL_INTERVAL_SECONDS}",
                            f"temp_workspace={temp_root}",
                            f"work_dir={work_dir}",
                            f"retained_artifacts={artifacts_dir}",
                            f"observed_request_ids={approval_result['request_ids']}",
                            f"auto_approved_request_ids={approval_result['attempted_request_ids']}",
                            f"pending_request_ids={final_approvals['request_ids']}",
                            f"pending_request_payloads={final_approvals['request_payload_paths']}",
                        ]
                    )
                )

            self.assertTrue(target_root.is_dir(), f"target package missing: {target_root}")
            self.assertFalse((target_root / ".lgwf").exists(), f"target package leaked runtime state: {target_root / '.lgwf'}")

            for relative_path in ("AGENTS.md", "README.md", "entry_contract.json", "wf/workflow.lgwf"):
                file_path = target_root / relative_path
                with self.subTest(file=relative_path):
                    self.assertTrue(file_path.is_file(), f"missing file: {file_path}")
                    file_path.read_text(encoding="utf-8")

            stage_workflows = sorted(
                path
                for path in (target_root / "wf").glob("*/workflow.lgwf")
                if path.parent.name not in {"docs", "shared"}
            )
            self.assertGreaterEqual(len(stage_workflows), 2, f"missing stage workflows under {target_root / 'wf'}")
            for workflow_path in stage_workflows:
                with self.subTest(stage=workflow_path.parent.name):
                    self.assertTrue((workflow_path.parent / "scripts").is_dir(), workflow_path.parent)

            nested_workflows = [
                path
                for path in (target_root / "wf").glob("*/*/workflow.lgwf")
                if path.parent.parent.name not in {"docs", "shared"}
            ]
            self.assertEqual(nested_workflows, [], f"unexpected nested workflow files: {nested_workflows}")

            self.assertTrue((target_root / "tests").is_dir(), f"missing tests dir: {target_root / 'tests'}")
            self.assertTrue(
                list((target_root / "tests").glob("test_*.py")),
                f"missing generated unittest file under {target_root / 'tests'}",
            )

            package_docs = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (target_root / "README.md", target_root / "AGENTS.md", target_root / "entry_contract.json")
                if path.is_file()
            ).casefold()
            for expected_text in (
                "repo-context-pack",
                "target_dir",
                "output_dir",
                "context",
                "handoff",
                "只读",
            ):
                self.assertIn(expected_text.casefold(), package_docs)

            created_package_audit = run_completed(
                [sys.executable, str(lgwf_py), "audit", str(target_root / "wf" / "workflow.lgwf")],
                cwd=temp_root,
                env=env,
                stdout_path=artifacts_dir / "generated_package_audit.stdout.txt",
                stderr_path=artifacts_dir / "generated_package_audit.stderr.txt",
                timeout_seconds=240,
            )
            self.assertEqual(
                created_package_audit.returncode,
                0,
                "\n".join(
                    [
                        "生成出的目标 package 未通过 authoring audit。",
                        f"temp_workspace={temp_root}",
                        f"stdout={artifacts_dir / 'generated_package_audit.stdout.txt'}",
                        f"stderr={artifacts_dir / 'generated_package_audit.stderr.txt'}",
                    ]
                ),
            )

            package_unittest = run_completed(
                [sys.executable, "-m", "unittest", "discover", "tests"],
                cwd=target_root,
                env=env,
                stdout_path=artifacts_dir / "generated_package_unittest.stdout.txt",
                stderr_path=artifacts_dir / "generated_package_unittest.stderr.txt",
                timeout_seconds=240,
            )
            self.assertEqual(
                package_unittest.returncode,
                0,
                "\n".join(
                    [
                        "生成出的目标 package 最小 unittest 未通过。",
                        f"temp_workspace={temp_root}",
                        f"stdout={artifacts_dir / 'generated_package_unittest.stdout.txt'}",
                        f"stderr={artifacts_dir / 'generated_package_unittest.stderr.txt'}",
                    ]
                ),
            )

            report_path = work_dir / REPORT_RELATIVE
            self.assertTrue(report_path.is_file(), f"missing report: {report_path}")
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn(WORKFLOW_NAME, report_text)
            self.assertIn(TARGET_PACKAGE_ROOT, report_text)
            self.assertIn("python -m unittest discover tests", report_text)
            self.assertTrue(output_json_path.is_file(), f"missing output json: {output_json_path}")

            success = True
        finally:
            if success:
                shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
