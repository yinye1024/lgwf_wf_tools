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


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[5]
WORKFLOW_LGWF = ROOT / "wf" / "workflow.lgwf"


def find_lgwf() -> Path:
    explicit = os.environ.get("LGWF_CLIENT_ASSIST_LGWF_PY")
    if explicit:
        return Path(explicit)
    lgwf_py = ROOT.parents[1] / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
    if not lgwf_py.is_file():
        raise FileNotFoundError(f"missing bundled lgwf-client-assist: {lgwf_py}")
    return lgwf_py


LGWF = find_lgwf()


def real_e2e_timeout_seconds() -> int:
    raw = os.environ.get("LGWF_LGWF_WF_PROMPT_UPGRADE_REAL_CODEX_E2E_TIMEOUT_SECONDS", "3600")
    try:
        value = int(raw)
    except ValueError as exc:
        raise AssertionError("LGWF_LGWF_WF_PROMPT_UPGRADE_REAL_CODEX_E2E_TIMEOUT_SECONDS must be an integer") from exc
    if value <= 0:
        raise AssertionError("LGWF_LGWF_WF_PROMPT_UPGRADE_REAL_CODEX_E2E_TIMEOUT_SECONDS must be positive")
    return value


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def preserve_artifacts(temp_root: Path, reason: str) -> Path:
    target_root = ROOT / "tests" / ".tmp"
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = target_root / f"real-positive-{stamp}-{reason}"
    shutil.copytree(temp_root, target, dirs_exist_ok=True)
    return target


def initial_target_payload(package_root: Path) -> dict[str, Any]:
    resolved = str(package_root.resolve())
    return {
        "target_workflow_lgwf": str((package_root / "workflow.lgwf").resolve()),
        "target_package_root": resolved,
        "target_dirs": [resolved],
    }


def create_minimal_target_package(package_root: Path) -> dict[str, str]:
    weak_prompt = """# Role

你是一个助手。

## Task

根据输入完成工作。
"""
    approve_prompt = """# Confirm

请确认是否继续。
"""
    workflow = """WORKFLOW target_prompt_upgrade_fixture;
ENTRY draft_copy;

REACT draft_copy MAX 1
  ACT CODEX
    PROMPT "agents/weak_prompt.md"
    RESULT state.target_prompt_upgrade_fixture.draft_copy_result;

APPROVAL confirm_release
  PROMPT_REF "approve.md"
  READ state.target_prompt_upgrade_fixture.confirm_context
  WRITE state.target_prompt_upgrade_fixture.confirm_result
  RESULT state.target_prompt_upgrade_fixture.confirm_release_result
  POLL 1;

FLOW draft_copy
  THEN confirm_release;
"""
    write_text(package_root / "workflow.lgwf", workflow)
    write_text(package_root / "agents" / "weak_prompt.md", weak_prompt)
    write_text(package_root / "approve.md", approve_prompt)
    return {
        "agents/weak_prompt.md": weak_prompt,
        "approve.md": approve_prompt,
    }


def approval_request_id(status: dict[str, Any]) -> str | None:
    request_id = status.get("human_request_id")
    pending = status.get("pending_human_requests") or []
    if request_id is None and pending:
        return pending[0].get("request_id")
    return request_id


def structured_contract_markers(text: str) -> int:
    markers = (
        "## Inputs",
        "## Task",
        "## Output Format",
        "## Success Criteria",
        "## Constraints",
        "## 输入",
        "## 任务",
        "## 输出格式",
        "## 成功标准",
        "## 约束",
    )
    return sum(1 for marker in markers if marker in text)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    # 真实 Codex E2E 是人工验收入口，不纳入 unittest discover 回归集合。
    return unittest.TestSuite()


class PromptUpgradeRealPositiveEndToEndTest(unittest.TestCase):
    def test_real_codex_positive_business_flow_upgrades_target_prompt(self) -> None:
        if not LGWF.exists():
            self.skipTest(f"lgwf.py not found: {LGWF}")

        temp_root = Path(tempfile.mkdtemp(prefix="lgwf-wf-prompt-upgrade-real-positive-"))
        work_dir = temp_root / "work"
        target_package = work_dir / "target-package"
        log_file = temp_root / "workflow.log"
        work_dir.mkdir()
        target_package.mkdir()
        baseline = create_minimal_target_package(target_package)
        pid: int | None = None
        preserve = os.environ.get("LGWF_LGWF_WF_PROMPT_UPGRADE_REAL_CODEX_E2E_KEEP_WORKDIR") == "1"
        env = dict(os.environ)

        try:
            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(WORKFLOW_LGWF),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    json.dumps({"scenario": "real_positive_minimal_prompt_contract_upgrade"}, ensure_ascii=False),
                    "--background",
                    "--log-file",
                    str(log_file),
                    "--rerun-existing",
                ],
                env=env,
                timeout=180,
            )
            self.assertEqual(launch.returncode, 0, launch.stderr + launch.stdout)
            pid = parse_json_object(launch.stdout, {"pid"})["pid"]

            seen_request_ids: list[str] = []
            repeat_counts: dict[str, int] = {}
            submitted_confirmation = False
            final_status: dict[str, Any] | None = None
            deadline = time.monotonic() + real_e2e_timeout_seconds()

            while time.monotonic() < deadline:
                status_result = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], env=env, timeout=60)
                self.assertEqual(status_result.returncode, 0, status_result.stderr + status_result.stdout)
                status = parse_json_object(status_result.stdout, {"running"})
                final_status = status
                if status.get("running") is False or status.get("phase") == "completed":
                    break

                request_id = approval_request_id(status)
                if not request_id:
                    time.sleep(2)
                    continue

                repeat_counts[request_id] = repeat_counts.get(request_id, 0) + 1
                self.assertLessEqual(
                    repeat_counts[request_id],
                    10,
                    f"approval {request_id} repeated without progress: {status}",
                )

                approval_get = run_lgwf(
                    ["approval", "get", "--work-dir", str(work_dir), "--request-id", str(request_id)],
                    env=env,
                    timeout=60,
                )
                self.assertEqual(approval_get.returncode, 0, approval_get.stderr + approval_get.stdout)
                approval_request = parse_json_object(approval_get.stdout, {"request_id"})
                seen_request_ids.append(request_id)
                prompt = str(approval_request.get("prompt") or "")
                context = approval_request.get("context")

                if "prompt-upgrade 目标 workflow 信息" in prompt:
                    value = initial_target_payload(target_package)
                    decision = "approve"
                elif isinstance(context, dict) and context.get("ready_for_confirmation") is True:
                    self.assertTrue(context.get("prompt_upgrades"), context)
                    self.assertTrue(context.get("files_to_modify"), context)
                    value = {"approve": True}
                    decision = "approve"
                    submitted_confirmation = True
                else:
                    self.fail(f"unexpected approval prompt={prompt!r} context={context!r}")

                submit = run_lgwf(
                    [
                        "approval",
                        "submit",
                        "--work-dir",
                        str(work_dir),
                        "--request-id",
                        str(request_id),
                        "--decision",
                        decision,
                        "--value-json",
                        json.dumps(value, ensure_ascii=False),
                        "--comment",
                        "real positive E2E auto approval",
                    ],
                    env=env,
                    timeout=60,
                )
                self.assertEqual(submit.returncode, 0, submit.stderr + submit.stdout)
                time.sleep(1)
            else:
                log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
                preserved = preserve_artifacts(temp_root, "timeout")
                self.fail(f"workflow did not finish before timeout; preserved={preserved}; log:\n{log[-8000:]}")

            self.assertIsNotNone(final_status)
            self.assertEqual(final_status.get("phase"), "completed", final_status)
            self.assertTrue(submitted_confirmation, seen_request_ids)

            prompt_upgrade_root = work_dir / ".lgwf" / "prompt_upgrade"
            summary_path = work_dir / ".lgwf" / "target_prompt_upgrade_summary.json"
            self.assertTrue((work_dir / ".lgwf" / "prompt_upgrade_target.json").exists())
            self.assertTrue((prompt_upgrade_root / "decision.json").exists())
            self.assertTrue(summary_path.exists())

            weak_prompt_path = target_package / "agents" / "weak_prompt.md"
            weak_prompt_final = weak_prompt_path.read_text(encoding="utf-8")
            self.assertNotEqual(weak_prompt_final, baseline["agents/weak_prompt.md"])
            self.assertGreaterEqual(structured_contract_markers(weak_prompt_final), 2, weak_prompt_final)

            changed_files = [
                relative
                for relative, baseline_text in baseline.items()
                if (target_package / relative).read_text(encoding="utf-8") != baseline_text
            ]
            self.assertTrue(changed_files, "expected at least one target prompt file to change")

            summary = read_json(summary_path)
            self.assertEqual(summary["status"], "upgraded")
            files_to_modify = summary.get("files_to_modify")
            self.assertIsInstance(files_to_modify, list)
            self.assertTrue(files_to_modify)
            self.assertTrue(any(relative in files_to_modify for relative in changed_files), summary)
        except Exception:
            preserved = preserve_artifacts(temp_root, "failure")
            print(f"preserved real E2E artifacts at {preserved}")
            raise
        finally:
            if pid is not None:
                run_lgwf(["stop", "--pid", str(pid)], env=env, timeout=30)
            if preserve:
                preserved = preserve_artifacts(temp_root, "kept")
                print(f"preserved real E2E artifacts at {preserved}")
            else:
                shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
