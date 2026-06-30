from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
from contextlib import ExitStack
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


def append_jsonl(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def runtime_temp_dir(stack: ExitStack, prefix: str, keep_env: str) -> str:
    if os.environ.get(keep_env) == "1":
        return tempfile.mkdtemp(prefix=prefix)
    return stack.enter_context(tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True))


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
            main_prompt_path = _extract_main_prompt_path(command[-1])
            metadata = {
                "instruction_id": (
                    main_prompt_path.replace("/", "__").replace(".md", "").replace("\\", "__")
                    if main_prompt_path
                    else "unknown_instruction"
                ),
                "main_prompt_path": main_prompt_path,
                "cwd": str(work_dir),
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


def write_fake_skill_dir(root: Path) -> Path:
    skill_dir = root / "lgwf-client-assist"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "AGENTS.md").write_text("# lgwf-client-assist\n", encoding="utf-8")
    return skill_dir


def copy_target_package(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git", ".lgwf", "tests", "ws_*"),
    )


def initial_target_payload(package_root: Path) -> dict[str, Any]:
    return {
        "target_workflow_lgwf": str((package_root / "wf" / "workflow.lgwf").resolve()),
        "target_package_root": str(package_root.resolve()),
        "target_dirs": [str(package_root.resolve())],
    }


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


MAIN_PROMPT_TO_NODE = {
    "02_design_upgrade/agents/reason.md": "design_prompt_upgrade__reason",
    "02_design_upgrade/agents/act.md": "design_prompt_upgrade__act",
    "02_design_upgrade/agents/observe.md": "design_prompt_upgrade__observe",
    "04_apply_upgrade/agents/reason.md": "apply_prompt_upgrade__reason",
    "04_apply_upgrade/agents/act.md": "apply_prompt_upgrade__act",
    "04_apply_upgrade/agents/observe.md": "apply_prompt_upgrade__observe",
}


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def extract_handoff_prompt(argv: list[str]) -> tuple[str, pathlib.Path | None]:
    prompt_path: pathlib.Path | None = None
    for index, arg in enumerate(argv[1:], start=1):
        if arg == "--prompt-file" and index + 1 < len(argv):
            prompt_path = pathlib.Path(argv[index + 1])
            return prompt_path.read_text(encoding="utf-8"), prompt_path
        if arg.startswith("--prompt-file="):
            prompt_path = pathlib.Path(arg.split("=", 1)[1])
            return prompt_path.read_text(encoding="utf-8"), prompt_path
    stdin_text = sys.stdin.read()
    if stdin_text:
        return stdin_text, prompt_path
    return "", prompt_path


def extract_main_prompt_path(prompt_text: str) -> str:
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


def call_state_path(root: pathlib.Path) -> pathlib.Path:
    return root / ".lgwf" / "fake_codex_call_state.json"


def next_call_index(root: pathlib.Path, node_key: str) -> int:
    path = call_state_path(root)
    state = {}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    state[node_key] = int(state.get(node_key, 0)) + 1
    write_json(path, state)
    return int(state[node_key])


def prompt_upgrade_root(workspace: pathlib.Path) -> pathlib.Path:
    return workspace / ".lgwf" / "prompt_upgrade"


def read_json(path: pathlib.Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def target_paths(workspace: pathlib.Path) -> dict[str, pathlib.Path]:
    target = read_json(workspace / ".lgwf" / "prompt_upgrade_target.json", {})
    package_root = pathlib.Path(target["target_package_root"])
    workflow_lgwf = pathlib.Path(target["target_workflow_lgwf"])
    return {"package_root": package_root, "workflow_lgwf": workflow_lgwf}


def write_analysis(workspace: pathlib.Path) -> list[str]:
    out = prompt_upgrade_root(workspace) / "analysis.json"
    write_json(
        out,
        {
            "summary": "已识别目标 workflow、prompt inventory 与可执行升级范围。",
            "artifact_root": ".lgwf/prompt_upgrade",
            "target_workflow": "lgwf_wf_prompt_upgrade",
            "analysis_focus": ["design contract", "apply contract", "runtime fake stability"],
        },
    )
    return [".lgwf/prompt_upgrade/analysis.json"]


def write_proposal(workspace: pathlib.Path) -> list[str]:
    out = prompt_upgrade_root(workspace) / "proposal.json"
    write_json(
        out,
        {
            "artifact_root": ".lgwf/prompt_upgrade",
            "summary": "提议收紧 design/apply prompt 的结构化输出契约。",
            "target_outcome": "让 prompt-upgrade workflow 的 prompt 更稳定、可消费、可验收。",
            "prompt_upgrades": [
                {
                    "id": "upgrade_runtime_fake_generation_contract",
                    "prompt_path": "wf/04_apply_upgrade/agents/act.md",
                    "workflow_path": "wf/workflow.lgwf",
                    "node_id": "apply_prompt_upgrade",
                    "react_phase": "act",
                    "current_gap": "执行摘要字段过于松散。",
                    "upgrade_intent": "增加更稳定的结构化执行摘要。",
                    "evidence": "runtime fake E2E 需要可观察修改。",
                    "role_design": "执行 agent 只按 apply_plan 修改指定文件。",
                    "responsibilities": ["修改指定文件", "输出结构化摘要"],
                    "required_knowledge": ["apply_plan schema"],
                    "required_tools": ["filesystem"],
                    "output_contract_changes": ["增加可观察摘要字段"],
                    "before_contract": {"inputs": [], "outputs": [], "quality_bar": "basic"},
                    "after_contract": {"inputs": [], "outputs": [], "quality_bar": "structured"},
                    "non_goals": ["不修改 runtime artifact"],
                    "tradeoffs": ["输出更长，但更稳定"],
                    "value_score": {
                        "impact": 3,
                        "confidence": 3,
                        "user_value": 3,
                        "implementation_cost": 1,
                        "risk": 1,
                        "rationale": "低风险高收益",
                    },
                    "quality_metrics": ["modified_files 可审计"],
                    "planned_changes": [
                        {
                            "file": "wf/04_apply_upgrade/agents/act.md",
                            "change": "补充执行摘要字段约束",
                            "reason": "增强可观察性",
                        }
                    ],
                    "acceptance_checks": ["modified_files 可观察", "summary 稳定"],
                    "risk_controls": ["不越界修改"],
                }
            ],
            "files_to_modify": ["wf/04_apply_upgrade/agents/act.md"],
            "quality_metrics": ["proposal contains non-empty upgrades"],
            "acceptance_checks": ["files_to_modify within target package"],
            "risks": ["target package is test copy only"],
            "deferred_upgrades": [],
        },
    )
    return [".lgwf/prompt_upgrade/proposal.json"]


def write_proposal_review(workspace: pathlib.Path) -> list[str]:
    out = prompt_upgrade_root(workspace) / "proposal_review.json"
    write_json(
        out,
        {
            "passed": True,
            "ready_for_confirmation": True,
            "blocking_issues": [],
            "summary": "proposal 可进入人工确认。",
        },
    )
    return [".lgwf/prompt_upgrade/proposal_review.json"]


def write_apply_plan(workspace: pathlib.Path) -> list[str]:
    root = prompt_upgrade_root(workspace)
    proposal = read_json(root / "proposal.json", {})
    decision = read_json(root / "decision.json", {})
    files_to_modify = proposal.get("files_to_modify") if isinstance(proposal.get("files_to_modify"), list) else []
    approved_upgrade_ids = (
        decision.get("approved_upgrade_ids") if isinstance(decision.get("approved_upgrade_ids"), list) else []
    )
    write_json(
        root / "apply_plan.json",
        {
            "status": "ready",
            "approved_upgrade_ids": approved_upgrade_ids,
            "files_to_modify": files_to_modify,
            "steps": [
                {
                    "step_id": "step_1",
                    "upgrade_id": "upgrade_runtime_fake_generation_contract",
                    "file": "wf/04_apply_upgrade/agents/act.md",
                    "intent": "补充稳定执行摘要契约。",
                }
            ],
        },
    )
    return [".lgwf/prompt_upgrade/apply_plan.json"]


def apply_changes(workspace: pathlib.Path) -> list[str]:
    paths = target_paths(workspace)
    plan = read_json(prompt_upgrade_root(workspace) / "apply_plan.json", {})
    changed_files: list[str] = []
    for relative in plan.get("files_to_modify", []):
        file_path = paths["package_root"] / relative
        original = file_path.read_text(encoding="utf-8")
        marker = "\n<!-- runtime fake e2e applied -->\n"
        if marker not in original:
            file_path.write_text(original.rstrip() + marker, encoding="utf-8")
        changed_files.append(relative)
    return changed_files


def write_apply_review(workspace: pathlib.Path) -> list[str]:
    changed_files = read_json(prompt_upgrade_root(workspace) / "changed_files.json", [])
    write_json(
        prompt_upgrade_root(workspace) / "apply_review.json",
        {
            "passed": True,
            "remaining_upgrade_ids": [],
            "changed_files": changed_files,
            "issues": [],
        },
    )
    return [".lgwf/prompt_upgrade/apply_review.json"]


def main(argv: list[str]) -> int:
    prompt_text, prompt_path = extract_handoff_prompt(argv)
    metadata = load_metadata(prompt_path)
    main_prompt_path = str(metadata.get("main_prompt_path") or extract_main_prompt_path(prompt_text))
    instruction_id = str(metadata.get("instruction_id") or "")
    workspace = pathlib.Path(str(metadata.get("cwd") or pathlib.Path.cwd()))
    calls_log = workspace / ".lgwf" / "fake_codex_calls.jsonl"

    matched_suffix = next((suffix for suffix in MAIN_PROMPT_TO_NODE if main_prompt_path.endswith(suffix)), "")
    if not matched_suffix:
        write_json(
            workspace / ".lgwf" / "fake_codex_unmatched.json",
            {
                "instruction_id": instruction_id,
                "main_prompt_path": main_prompt_path,
                "prompt_file": str(prompt_path) if prompt_path else "",
                "reason": "no stable mapping matched main prompt path",
            },
        )
        return 2

    node_key = MAIN_PROMPT_TO_NODE[matched_suffix]
    call_index = next_call_index(workspace, node_key)
    output_files: list[str]

    if node_key == "design_prompt_upgrade__reason":
        output_files = write_analysis(workspace)
    elif node_key == "design_prompt_upgrade__act":
        output_files = write_proposal(workspace)
    elif node_key == "design_prompt_upgrade__observe":
        output_files = write_proposal_review(workspace)
    elif node_key == "apply_prompt_upgrade__reason":
        output_files = write_apply_plan(workspace)
    elif node_key == "apply_prompt_upgrade__act":
        changed_files = apply_changes(workspace)
        write_json(prompt_upgrade_root(workspace) / "changed_files.json", changed_files)
        output_files = changed_files
    else:
        output_files = write_apply_review(workspace)

    append_jsonl(
        calls_log,
        {
            "instruction_id": instruction_id,
            "main_prompt_path": main_prompt_path,
            "node_key": node_key,
            "call_index": call_index,
            "output_files": output_files,
        },
    )
    payload = {
        "ok": True,
        "node_key": node_key,
        "call_index": call_index,
        "output_files": output_files,
    }
    if len(output_files) == 1 and output_files[0].startswith(".lgwf/prompt_upgrade/") and output_files[0].endswith(".json"):
        artifact = workspace / output_files[0]
        if artifact.exists():
            loaded = read_json(artifact, {})
            if isinstance(loaded, dict):
                payload.update(loaded)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''.lstrip(),
        encoding="utf-8",
    )
    for name in ("codex.cmd", "codex.bat"):
        (fake_bin / name).write_text(f'@echo off\r\npython "%~dp0fake_codex.py" %*\r\n', encoding="utf-8")


def scenario_fake_responses(scenario_id: str) -> list[dict[str, Any]]:
    responses = [
        {
            "node_id": "design_prompt_upgrade",
            "phase": "reason",
            "call_index": 1,
            "output_files": [".lgwf/prompt_upgrade/analysis.json"],
        },
        {
            "node_id": "design_prompt_upgrade",
            "phase": "act",
            "call_index": 1,
            "output_files": [".lgwf/prompt_upgrade/proposal.json"],
        },
        {
            "node_id": "design_prompt_upgrade",
            "phase": "observe",
            "call_index": 1,
            "output_files": [".lgwf/prompt_upgrade/proposal_review.json"],
        },
    ]
    if scenario_id == "happy_path":
        responses.extend(
            [
                {
                    "node_id": "apply_prompt_upgrade",
                    "phase": "reason",
                    "call_index": 1,
                    "output_files": [".lgwf/prompt_upgrade/apply_plan.json"],
                },
                {
                    "node_id": "apply_prompt_upgrade",
                    "phase": "act",
                    "call_index": 1,
                    "output_files": ["wf/04_apply_upgrade/agents/act.md"],
                },
                {
                    "node_id": "apply_prompt_upgrade",
                    "phase": "observe",
                    "call_index": 1,
                    "output_files": [".lgwf/prompt_upgrade/apply_review.json"],
                },
            ]
        )
    return responses


class FakeCodexContractTest(unittest.TestCase):
    def test_fake_codex_routes_by_main_prompt_path_and_writes_design_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lgwf-prompt-upgrade-fake-codex-") as temp:
            temp_root = Path(temp)
            fake_bin = temp_root / "fake-bin"
            work_dir = temp_root / "work"
            package_root = work_dir / "target-package"
            copy_target_package(package_root)
            write_fake_codex(fake_bin)
            write_json(work_dir / ".lgwf" / "prompt_upgrade_target.json", initial_target_payload(package_root))
            prompt_root = temp_root / "prompt"
            prompt_root.mkdir()
            prompt_path = prompt_root / "handoff_prompt.txt"
            prompt_path.write_text(
                fake_handoff("D:/snapshot/02_design_upgrade/agents/act.md"),
                encoding="utf-8",
            )
            write_json(
                prompt_root / "metadata.json",
                {
                    "instruction_id": "design_prompt_upgrade__act",
                    "main_prompt_path": "02_design_upgrade/agents/act.md",
                    "cwd": str(work_dir),
                },
            )

            result = subprocess.run(
                ["python", str(fake_bin / "fake_codex.py"), "exec", "--prompt-file", str(prompt_path)],
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["node_key"], "design_prompt_upgrade__act")
            proposal = read_json(work_dir / ".lgwf" / "prompt_upgrade" / "proposal.json")
            self.assertTrue(proposal["prompt_upgrades"])
            calls = [json.loads(line) for line in (work_dir / ".lgwf" / "fake_codex_calls.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(calls[0]["call_index"], 1)
            self.assertEqual(calls[0]["main_prompt_path"], "02_design_upgrade/agents/act.md")

    def test_fake_codex_fails_fast_when_mapping_is_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lgwf-prompt-upgrade-fake-codex-miss-") as temp:
            temp_root = Path(temp)
            fake_bin = temp_root / "fake-bin"
            work_dir = temp_root / "work"
            write_fake_codex(fake_bin)
            prompt_root = temp_root / "prompt"
            prompt_root.mkdir()
            prompt_path = prompt_root / "handoff_prompt.txt"
            prompt_path.write_text(fake_handoff("D:/snapshot/unknown/act.md"), encoding="utf-8")
            write_json(
                prompt_root / "metadata.json",
                {
                    "instruction_id": "unknown",
                    "main_prompt_path": "unknown/act.md",
                    "cwd": str(work_dir),
                },
            )

            result = subprocess.run(
                ["python", str(fake_bin / "fake_codex.py"), "exec", "--prompt-file", str(prompt_path)],
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            unmatched = read_json(work_dir / ".lgwf" / "fake_codex_unmatched.json")
            self.assertEqual(unmatched["instruction_id"], "unknown")
            self.assertEqual(unmatched["main_prompt_path"], "unknown/act.md")


@unittest.skipUnless(LGWF.exists(), f"LGWF facade not found: {LGWF}")
class PromptUpgradeRuntimeFakeEndToEndTest(unittest.TestCase):
    def _prepare_runtime(self, stack: ExitStack, prefix: str) -> tuple[dict[str, str], Path, Path]:
        temp = runtime_temp_dir(stack, prefix, "LGWF_WF_PROMPT_UPGRADE_RUNTIME_FAKE_KEEP_WORKDIR")
        temp_root = Path(temp)
        fake_bin = temp_root / "fake-bin"
        patch_dir = temp_root / "pythonpath"
        work_dir = temp_root / "work"
        target_package = work_dir / "target-package"
        log_file = temp_root / "workflow.log"
        write_fake_codex(fake_bin)
        write_prompt_file_mode_patch(patch_dir)
        work_dir.mkdir()
        copy_target_package(target_package)
        skill_dir = write_fake_skill_dir(temp_root)

        env = dict(os.environ)
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(patch_dir) + os.pathsep + env.get("PYTHONPATH", "")
        env["LGWF_FAKE_CODEX_WORK_DIR"] = str(work_dir)
        env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
        env["LGWF_CLIENT_ASSIST"] = str(skill_dir)
        env["LGWF_CLIENT_ASSIST_SKILL_DIR"] = str(skill_dir)
        env["LGWF_ALLOW_TEST_CLIENT_ASSIST_ENV"] = "1"
        return env, work_dir, log_file

    def _wait_for_status(self, pid: int, work_dir: Path, env: dict[str, str], timeout_seconds: int = 30) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_status: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            status_result = run_lgwf(["status", "--pid", str(pid), "--work-dir", str(work_dir)], env=env, timeout=30)
            self.assertEqual(status_result.returncode, 0, status_result.stderr + status_result.stdout)
            last_status = parse_json_object(status_result.stdout, {"running"})
            request_id = last_status.get("human_request_id")
            pending = last_status.get("pending_human_requests") or []
            if request_id or pending or last_status.get("running") is False or last_status.get("phase") == "completed":
                return last_status
            time.sleep(1)
        raise AssertionError(f"workflow did not surface status within {timeout_seconds}s: {last_status}")

    def _approval_request_id(self, status: dict[str, Any]) -> str | None:
        request_id = status.get("human_request_id")
        pending = status.get("pending_human_requests") or []
        if request_id is None and pending:
            return pending[0].get("request_id")
        return request_id

    def _submit_approval(
        self,
        *,
        pid: int,
        work_dir: Path,
        env: dict[str, str],
        request_id: str,
        value: dict[str, Any],
        decision: str,
    ) -> dict[str, Any]:
        submit = run_lgwf(
            [
                "approval",
                "submit",
                "--work-dir",
                str(work_dir),
                "--request-id",
                request_id,
                "--decision",
                decision,
                "--value-json",
                json.dumps(value, ensure_ascii=False),
                "--comment",
                "runtime fake e2e auto approval",
            ],
            env=env,
            timeout=30,
        )
        self.assertEqual(submit.returncode, 0, submit.stderr + submit.stdout)
        deadline = time.monotonic() + 20
        last_status: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            status = self._wait_for_status(pid, work_dir, env, timeout_seconds=5)
            last_status = status
            if status.get("running") is False or status.get("phase") in {"completed", "failed", "cancelled", "timed_out"}:
                return status
            if self._approval_request_id(status) != request_id:
                return status
            time.sleep(1)
        raise AssertionError(f"approval {request_id} did not advance within 20s: {last_status}")

    def _run_scenario(
        self,
        scenario_id: str,
        confirm_value: dict[str, Any],
        confirm_decision: str,
        expected_phase: str = "completed",
    ) -> tuple[Path, dict[str, Any]]:
        retryable_launch_markers = ("PermissionError", "拒绝访问", ".pid.json")
        for attempt in range(1, 4):
            stack = ExitStack()
            env, work_dir, log_file = self._prepare_runtime(stack, f"lgwf-prompt-upgrade-{scenario_id}-")
            target_package = work_dir / "target-package"
            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(WORKFLOW_LGWF),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    json.dumps({"scenario": scenario_id}, ensure_ascii=False),
                    "--background",
                    "--log-file",
                    str(log_file),
                ],
                env=env,
                timeout=30,
            )
            if launch.returncode == 0:
                self.addCleanup(stack.close)
                break
            launch_text = launch.stderr + launch.stdout
            stack.close()
            if attempt == 3 or not any(marker in launch_text for marker in retryable_launch_markers):
                self.fail(launch_text)
            time.sleep(1)
        else:
            self.fail("unreachable launch retry state")

        pid = parse_json_object(launch.stdout, {"pid"})["pid"]
        stack.callback(lambda: run_lgwf(["stop", "--pid", str(pid)], env=env, timeout=30))

        seen_request_ids: list[str] = []
        repeat_counts: dict[str, int] = {}
        final_status: dict[str, Any] | None = None
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            status = self._wait_for_status(pid, work_dir, env, timeout_seconds=10)
            final_status = status
            if status.get("running") is False or status.get("phase") == "completed":
                break
            request_id = self._approval_request_id(status)
            self.assertIsNotNone(request_id, f"expected pending approval, got status={status}")
            repeat_counts[request_id] = repeat_counts.get(request_id, 0) + 1
            self.assertLessEqual(repeat_counts[request_id], 3, f"approval {request_id} repeated without progress: {status}")

            approval_get = run_lgwf(
                ["approval", "get", "--work-dir", str(work_dir), "--request-id", str(request_id)],
                env=env,
                timeout=30,
            )
            self.assertEqual(approval_get.returncode, 0, approval_get.stderr + approval_get.stdout)
            approval_request = parse_json_object(approval_get.stdout, {"request_id"})
            prompt = str(approval_request.get("prompt") or "")
            context = approval_request.get("context")
            seen_request_ids.append(request_id)

            is_entry_approval = (
                "prompt-upgrade 目标 workflow 信息" in prompt
                or all(
                    marker in prompt
                    for marker in (
                        "target_workflow_lgwf",
                        "target_package_root",
                        "target_dirs",
                    )
                )
            )

            if is_entry_approval:
                self.assertTrue(isinstance(context, dict) or context in ({}, None))
                status = self._submit_approval(
                    pid=pid,
                    work_dir=work_dir,
                    env=env,
                    request_id=request_id,
                    value=initial_target_payload(target_package),
                    decision="approve",
                )
            elif (
                isinstance(context, dict)
                and isinstance(context.get("prompt_upgrades"), list)
                and isinstance(context.get("instructions"), dict)
            ):
                status = self._submit_approval(
                    pid=pid,
                    work_dir=work_dir,
                    env=env,
                    request_id=request_id,
                    value=confirm_value,
                    decision=confirm_decision,
                )
            else:
                self.fail(f"unexpected approval node prompt={prompt!r} context={context!r}")
            final_status = status
        else:
            log = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
            self.fail(f"workflow did not finish before timeout; log tail:\n{log[-8000:]}")

        self.assertIsNotNone(final_status)
        self.assertEqual(final_status.get("phase"), expected_phase, final_status)
        self.assertGreaterEqual(len(seen_request_ids), 2)

        summary = {
            "work_dir": work_dir,
            "target_package": target_package,
            "log_file": log_file,
            "final_status": final_status,
            "seen_request_ids": seen_request_ids,
        }
        return work_dir, summary

    def test_happy_path(self) -> None:
        work_dir, runtime = self._run_scenario("happy_path", {"approve": True}, "approve")
        prompt_root = work_dir / ".lgwf" / "prompt_upgrade"
        target = read_json(work_dir / ".lgwf" / "prompt_upgrade_target.json")
        self.assertTrue(Path(target["target_workflow_lgwf"]).is_absolute())
        self.assertTrue(Path(target["target_package_root"]).is_absolute())
        self.assertTrue(target["target_dirs"])
        self.assertTrue(read_json(prompt_root / "environment_check.json")["passed"])
        inventory = read_json(prompt_root / "inventory.json")
        self.assertTrue(inventory["prompts"])
        self.assertTrue((prompt_root / "proposal_review.json").is_file())
        self.assertEqual(read_json(prompt_root / "design_decision.json")["next"], "exit")
        decision = read_json(prompt_root / "decision.json")
        self.assertTrue(decision["approve"])
        self.assertTrue(decision["approved_upgrade_ids"])
        apply_plan = read_json(prompt_root / "apply_plan.json")
        self.assertEqual(apply_plan["status"], "ready")
        apply_review = read_json(prompt_root / "apply_review.json")
        self.assertTrue(apply_review["passed"])
        self.assertEqual(apply_review["remaining_upgrade_ids"], [])
        react_history = read_json(prompt_root / "react_history.json")
        self.assertEqual(react_history[-1]["next"], "exit")
        summary = read_json(work_dir / ".lgwf" / "target_prompt_upgrade_summary.json")
        self.assertEqual(summary["status"], "upgraded")
        changed_target_file = (
            Path(target["target_package_root"])
            / "wf"
            / "04_apply_upgrade"
            / "agents"
            / "act.md"
        )
        self.assertIn("runtime fake e2e applied", changed_target_file.read_text(encoding="utf-8"))
        calls = [json.loads(line) for line in (work_dir / ".lgwf" / "fake_codex_calls.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(calls), 6)
        self.assertEqual([item["node_key"] for item in calls], [resp["node_id"] + "__" + resp["phase"] for resp in scenario_fake_responses("happy_path")])
        self.assertFalse((work_dir / ".lgwf" / "fake_codex_unmatched.json").exists())
        self.assertEqual(runtime["final_status"]["phase"], "completed")

    def test_reject_to_summarize(self) -> None:
        work_dir, runtime = self._run_scenario(
            "reject_to_summarize",
            {"reject": True, "comment": "runtime fake reject branch"},
            "approve",
            expected_phase="failed",
        )
        prompt_root = work_dir / ".lgwf" / "prompt_upgrade"
        decision = read_json(prompt_root / "decision.json")
        self.assertTrue(decision["reject"])
        self.assertFalse((prompt_root / "apply_plan.json").exists())
        self.assertFalse((prompt_root / "apply_review.json").exists())
        self.assertFalse((work_dir / ".lgwf" / "target_prompt_upgrade_summary.json").exists())
        calls = [json.loads(line) for line in (work_dir / ".lgwf" / "fake_codex_calls.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(calls), 3)
        self.assertEqual([item["node_key"] for item in calls], [resp["node_id"] + "__" + resp["phase"] for resp in scenario_fake_responses("reject_to_summarize")])
        self.assertFalse((work_dir / ".lgwf" / "fake_codex_unmatched.json").exists())
        self.assertEqual(runtime["final_status"]["phase"], "failed")


if __name__ == "__main__":
    unittest.main()

