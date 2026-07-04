from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[3]
WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
LGWF = PACKAGE_ROOT.parent / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"

PROMPT_TO_NODE = {
    "wf/02_git_context_collection/agents/inspect_repo_state.md": "inspect_repo_state",
    "wf/03_brief_synthesis/agents/synthesize_change_summary.md": "identify_change_themes",
    "wf/03_brief_synthesis/agents/draft_markdown_brief.md": "compose_markdown_brief",
    "wf/04_result_review_and_delivery/agents/present_brief.md": "present_brief",
}

EXPECTED_CALL_ORDER = [
    "inspect_repo_state",
    "identify_change_themes",
    "compose_markdown_brief",
    "present_brief",
]
OUTPUT_JSON_FILES = [
    ".lgwf/request_scope_capture.json",
    ".lgwf/git_context_review.json",
    ".lgwf/change_summary_context.json",
    ".lgwf/change_brief_markdown.json",
    ".lgwf/delivery_review_context.json",
]
PERSIST_FILES = [
    ".lgwf/request_scope_confirmation.json",
    ".lgwf/delivery_decision.json",
    ".lgwf/commit_plan.json",
    ".lgwf/commit_action_result.json",
]
TERMINAL_PHASES = {"completed", "failed", "stopped"}

sys.dont_write_bytecode = True


def run_lgwf(args: list[str], *, env: dict[str, str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
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
    raise AssertionError(f"stdout 未包含所需 JSON 对象: keys={sorted(required_keys or set())}\n{text}")


def parse_status_payload(text: str) -> dict[str, Any]:
    payload = parse_json_object(text)
    accepted_keys = {
        "phase",
        "session_id",
        "pid",
        "current_node",
        "current_capability",
        "human_request_id",
        "pending_human_requests",
        "pending_action",
    }
    if accepted_keys.isdisjoint(payload):
        raise AssertionError(f"stdout 未包含 status JSON 对象: keys={sorted(accepted_keys)}\n{text}")
    return payload


def is_terminal_status(payload: dict[str, Any]) -> bool:
    phase = payload.get("phase")
    if isinstance(phase, str) and phase in TERMINAL_PHASES:
        return True
    status = payload.get("status")
    return isinstance(status, str) and status in TERMINAL_PHASES


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def build_markdown(lines: list[str]) -> str:
    return "# 变更摘要\n\n" + "\n".join(f"- {line}" for line in lines) + "\n"


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
            metadata = {
                "main_prompt_path": _extract_main_prompt_path(command[-1]),
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


def write_fake_codex(fake_bin: Path) -> None:
    fake_bin.mkdir(parents=True, exist_ok=True)
    (fake_bin / "fake_codex.py").write_text(
        r'''
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any


PROMPT_TO_NODE = {
    "wf/02_git_context_collection/agents/inspect_repo_state.md": "inspect_repo_state",
    "wf/03_brief_synthesis/agents/synthesize_change_summary.md": "identify_change_themes",
    "wf/03_brief_synthesis/agents/draft_markdown_brief.md": "compose_markdown_brief",
    "wf/04_result_review_and_delivery/agents/present_brief.md": "present_brief",
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
    return stdin_text, prompt_path


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
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def next_call_index(work_dir: pathlib.Path, node_id: str) -> int:
    state_path = work_dir / ".lgwf" / "fake_codex_call_state.json"
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    state[node_id] = int(state.get(node_id, 0)) + 1
    write_json(state_path, state)
    return int(state[node_id])


def find_response(scenario: dict[str, Any], node_id: str, call_index: int) -> dict[str, Any] | None:
    for response in scenario.get("fake_responses", []):
        if response.get("node_id") == node_id and int(response.get("call_index", 0)) == call_index:
            return response
    return None


def resolve_node_id(main_prompt_path: str) -> str:
    normalized = main_prompt_path.replace("\\", "/")
    for suffix, node_id in PROMPT_TO_NODE.items():
        runtime_suffix = suffix.removeprefix("wf/")
        if normalized.endswith(suffix) or normalized.endswith(runtime_suffix):
            return node_id
    return ""


def main(argv: list[str]) -> int:
    prompt_text, prompt_path = extract_handoff_prompt(argv)
    metadata = load_metadata(prompt_path)
    main_prompt_path = str(metadata.get("main_prompt_path") or extract_main_prompt_path(prompt_text))
    scenario_path = pathlib.Path(os.environ["LGWF_FAKE_CODEX_SCENARIO_FILE"])
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    work_dir = pathlib.Path(os.environ["LGWF_FAKE_CODEX_WORK_DIR"])
    log_path = work_dir / ".lgwf" / "fake_codex_calls.jsonl"
    unmatched_path = work_dir / ".lgwf" / "fake_codex_unmatched.json"
    resolved_node_id = resolve_node_id(main_prompt_path)

    if not resolved_node_id:
        append_jsonl(
            log_path,
            {
                "scenario_id": scenario.get("scenario_id"),
                "prompt_file": str(prompt_path) if prompt_path else "",
                "main_prompt_path": main_prompt_path,
                "unmapped_call": True,
                "available_mapping_keys": sorted(PROMPT_TO_NODE),
                "argv": argv[1:],
            },
        )
        write_json(
            unmatched_path,
            {
                "scenario_id": scenario.get("scenario_id"),
                "prompt_file": str(prompt_path) if prompt_path else "",
                "main_prompt_path": main_prompt_path,
                "unmapped_call": True,
                "available_mapping_keys": sorted(PROMPT_TO_NODE),
                "argv": argv[1:],
            },
        )
        print(json.dumps({"ok": False, "unmapped_call": True, "main_prompt_path": main_prompt_path}, ensure_ascii=False))
        return 2

    call_index = next_call_index(work_dir, resolved_node_id)
    response = find_response(scenario, resolved_node_id, call_index)
    if response is None:
        append_jsonl(
            log_path,
            {
                "scenario_id": scenario.get("scenario_id"),
                "prompt_file": str(prompt_path) if prompt_path else "",
                "main_prompt_path": main_prompt_path,
                "resolved_node_id": resolved_node_id,
                "call_index": call_index,
                "unmapped_call": True,
                "available_mapping_keys": [
                    {"node_id": item.get("node_id"), "call_index": item.get("call_index")}
                    for item in scenario.get("fake_responses", [])
                ],
                "argv": argv[1:],
            },
        )
        write_json(
            unmatched_path,
            {
                "scenario_id": scenario.get("scenario_id"),
                "prompt_file": str(prompt_path) if prompt_path else "",
                "main_prompt_path": main_prompt_path,
                "resolved_node_id": resolved_node_id,
                "call_index": call_index,
                "unmapped_call": True,
                "available_mapping_keys": [
                    {"node_id": item.get("node_id"), "call_index": item.get("call_index")}
                    for item in scenario.get("fake_responses", [])
                ],
                "argv": argv[1:],
            },
        )
        print(json.dumps({"ok": False, "unmapped_call": True, "resolved_node_id": resolved_node_id, "call_index": call_index}, ensure_ascii=False))
        return 2

    written_outputs: list[str] = []
    stdout_payload: Any = {
        "ok": True,
        "scenario_id": scenario.get("scenario_id"),
        "resolved_node_id": resolved_node_id,
        "call_index": call_index,
    }
    for relative_path, payload in response.get("writes", {}).items():
        output_path = work_dir / relative_path
        write_json(output_path, payload)
        written_outputs.append(relative_path)
        stdout_payload = payload

    append_jsonl(
        log_path,
        {
            "scenario_id": scenario.get("scenario_id"),
            "prompt_file": str(prompt_path) if prompt_path else "",
            "main_prompt_path": main_prompt_path,
            "resolved_node_id": resolved_node_id,
            "call_index": call_index,
            "unmapped_call": False,
            "written_outputs": written_outputs,
            "argv": argv[1:],
        },
    )
    print(
        json.dumps(
            stdout_payload,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''.lstrip(),
        encoding="utf-8",
    )
    for launcher in ("codex.cmd", "codex.bat"):
        (fake_bin / launcher).write_text('@echo off\r\npython "%~dp0fake_codex.py" %*\r\n', encoding="utf-8")


def scenario_payloads() -> dict[str, dict[str, Any]]:
    repo_hint = PACKAGE_ROOT.resolve().as_posix()
    happy_markdown = build_markdown(
        [
            "基于真实 Git 上下文生成当前变更摘要。",
            "关键命令包括 `git status --short`、`git diff --stat`、`git log -1 --stat`。",
            "当前风险集中在 fake Codex 响应未覆盖真实语义判断。",
        ]
    )
    happy_selection_prompt = "\n".join(
        [
            "本次变更摘要预览：",
            "",
            f"目标仓库：{repo_hint}",
            "变更文件数：2",
            "",
            "请选择本次最终交付动作：",
            "",
            "1. 接受摘要",
            "2. 接受摘要，并执行 git add",
            "3. 接受摘要，执行 git add，并创建 commit",
            "4. 返回修订摘要",
            "5. 拒绝并终止 workflow",
            "",
            "请回复 1、2、3、4 或 5。",
        ]
    )
    revised_markdown = build_markdown(
        [
            "请求范围已补充仓库边界说明，摘要链路继续执行。",
            "关键命令包括 `git status --short`、`git diff --stat`、`git log -1 --stat`。",
            "仍需人工关注 fake Codex 响应对最终判断的影响。",
        ]
    )
    return {
        "happy_path": {
            "scenario_id": "happy_path",
            "fake_responses": [
                {
                    "node_id": "inspect_repo_state",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/git_context_review.json": {
                            "passed": True,
                            "issues": ["Git 上下文来自真实采集脚本，fake Codex 仅验证编排结构。"],
                            "summary": "当前 Git 事实满足摘要编排验证要求。",
                        }
                    },
                },
                {
                    "node_id": "identify_change_themes",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/change_summary_context.json": {
                            "change_overview": [
                                "补齐 runtime fake E2E 的场景化验证入口。",
                                "对两道人工确认门禁建立可追踪的自动审批。",
                                "保留 fake Codex 响应，仅验证编排连通。",
                            ],
                            "key_files": [
                                "wf/workflow.lgwf",
                                "tests/test_git_diff_brief_runtime_fake_e2e.py",
                            ],
                            "risk_points": [
                                "Git 事实来自真实采集脚本，但摘要语义来自 fake Codex 响应。",
                                "真实 Codex 语义未纳入本测试覆盖。",
                            ],
                            "validation_candidates": [
                                "git status --short",
                                "git diff --stat",
                                "git log -1 --stat",
                            ],
                            "summary_supporting_context": {
                                "source": "fake runtime codex",
                                "context_kind": "real_git_context",
                            },
                            "commit_message_suggestion": "test(git-diff-brief): cover runtime fake approval flow",
                            "commit_message_rationale": "基于 runtime fake E2E 和审批链路相关变更生成。",
                        }
                    },
                },
                {
                    "node_id": "compose_markdown_brief",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/change_brief_markdown.json": {
                            "change_brief_markdown": happy_markdown,
                            "sections": ["变更概览", "关键文件", "风险点", "建议验证命令"],
                        }
                    },
                },
                {
                    "node_id": "present_brief",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/delivery_review_context.json": {
                            "delivery_review_input": {
                                "final_change_brief_markdown": happy_markdown,
                                "commit_message_suggestion": "test(git-diff-brief): cover runtime fake approval flow",
                                "commit_message_rationale": "基于 runtime fake E2E 和审批链路相关变更生成。",
                                "commit_action_options": ["none", "stage", "commit"],
                                "default_commit_action": "none",
                                "selection_prompt": happy_selection_prompt,
                                "open_delivery_questions": [],
                            },
                            "final_change_brief_markdown": happy_markdown,
                            "commit_message_suggestion": "test(git-diff-brief): cover runtime fake approval flow",
                            "commit_message_rationale": "基于 runtime fake E2E 和审批链路相关变更生成。",
                            "summary_supporting_context": {
                                "validation_candidates": [
                                    "git status --short",
                                    "git diff --stat",
                                    "git log -1 --stat",
                                ]
                            },
                            "open_delivery_questions": [],
                        }
                    },
                },
            ],
            "approval_steps": [
                {
                    "approval_node": "confirm_scope_if_needed",
                    "submit_value": {
                        "approval": "approve",
                        "comment": "最小范围成立，继续采集与摘要。",
                        "changes": [],
                    },
                },
                {
                    "approval_node": "confirm_delivery_or_revision",
                    "submit_value": {
                        "approval": "approve",
                        "commit_action": "none",
                        "stage_scope": "target_scope",
                        "commit_message": "test(git-diff-brief): cover runtime fake approval flow",
                        "comment": "接受当前摘要草稿并进入最终整理。",
                        "changes": [],
                    },
                },
            ],
        },
        "scope_revise_then_approve": {
            "scenario_id": "scope_revise_then_approve",
            "fake_responses": [
                {
                    "node_id": "inspect_repo_state",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/git_context_review.json": {
                            "passed": True,
                            "issues": ["Git 上下文来自真实采集脚本，fake Codex 仅验证编排结构。"],
                            "summary": "仓库范围修订后，Git 审计阶段继续通过。",
                        }
                    },
                },
                {
                    "node_id": "identify_change_themes",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/change_summary_context.json": {
                            "change_overview": [
                                "第一道审批走 revise 回路后重新生成请求范围上下文。",
                                "范围确认完成后继续执行 Git 审计与摘要链路。",
                            ],
                            "key_files": [
                                "wf/01_request_scope_alignment/workflow.lgwf",
                                "tests/test_git_diff_brief_runtime_fake_e2e.py",
                            ],
                            "risk_points": ["如果 revise 后未回到 capture_request_context，说明 route 错误。"],
                            "validation_candidates": [
                                "git status --short",
                                "git diff --stat",
                                "git log -1 --stat",
                            ],
                            "summary_supporting_context": {
                                "source": "fake runtime codex",
                                "context_kind": "real_git_context",
                            },
                            "commit_message_suggestion": "test(git-diff-brief): cover scope revision flow",
                            "commit_message_rationale": "基于范围修订回路和 fake runtime 编排验证生成。",
                        }
                    },
                },
                {
                    "node_id": "compose_markdown_brief",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/change_brief_markdown.json": {
                            "change_brief_markdown": revised_markdown,
                            "sections": ["变更概览", "关键文件", "风险点", "建议验证命令"],
                        }
                    },
                },
                {
                    "node_id": "present_brief",
                    "call_index": 1,
                    "writes": {
                        ".lgwf/delivery_review_context.json": {
                            "delivery_review_input": {
                                "final_change_brief_markdown": revised_markdown,
                                "commit_message_suggestion": "test(git-diff-brief): cover scope revision flow",
                                "commit_message_rationale": "基于范围修订回路和 fake runtime 编排验证生成。",
                                "commit_action_options": ["none", "stage", "commit"],
                                "default_commit_action": "none",
                                "selection_prompt": happy_selection_prompt,
                                "open_delivery_questions": [],
                            },
                            "final_change_brief_markdown": revised_markdown,
                            "commit_message_suggestion": "test(git-diff-brief): cover scope revision flow",
                            "commit_message_rationale": "基于范围修订回路和 fake runtime 编排验证生成。",
                            "summary_supporting_context": {
                                "validation_candidates": [
                                    "git status --short",
                                    "git diff --stat",
                                    "git log -1 --stat",
                                ]
                            },
                            "open_delivery_questions": [],
                        }
                    },
                },
            ],
            "approval_steps": [
                {
                    "approval_node": "confirm_scope_if_needed",
                    "submit_value": {
                        "approval": "revise",
                        "comment": "先模拟人工要求收敛请求范围。",
                        "changes": ["补充并确认仓库范围说明"],
                    },
                },
                {
                    "approval_node": "confirm_scope_if_needed",
                    "submit_value": {
                        "approval": "approve",
                        "comment": "第二次确认后接受当前范围。",
                        "changes": [],
                    },
                },
                {
                    "approval_node": "confirm_delivery_or_revision",
                    "submit_value": {
                        "approval": "approve",
                        "commit_action": "none",
                        "stage_scope": "target_scope",
                        "commit_message": "test(git-diff-brief): cover scope revision flow",
                        "comment": "范围回路通过后，接受最终摘要。",
                        "changes": [],
                    },
                },
            ],
        },
    }


def trace_dir(work_dir: Path, scenario_id: str) -> Path:
    return work_dir / ".lgwf" / "runtime_fake_trace" / scenario_id


@unittest.skipUnless(LGWF.is_file(), f"LGWF facade not found: {LGWF}")
class GitDiffBriefRuntimeFakeE2ETest(unittest.TestCase):
    maxDiff = None

    def _prepare_runtime(self, stack: ExitStack, scenario_id: str) -> tuple[dict[str, str], Path, Path]:
        temp = runtime_temp_dir(stack, f"git-diff-brief-runtime-fake-{scenario_id}-", "GIT_DIFF_BRIEF_RUNTIME_FAKE_KEEP_WORKDIR")
        temp_root = Path(temp)
        fake_bin = temp_root / "fake-bin"
        patch_dir = temp_root / "pythonpath"
        work_dir = temp_root / "work"
        scenario_file = temp_root / f"{scenario_id}.scenario.json"
        log_file = temp_root / "workflow.log"

        work_dir.mkdir(parents=True, exist_ok=True)
        write_fake_codex(fake_bin)
        write_prompt_file_mode_patch(patch_dir)
        write_json(scenario_file, scenario_payloads()[scenario_id])

        env = dict(os.environ)
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = str(patch_dir) + os.pathsep + env.get("PYTHONPATH", "")
        env["LGWF_FAKE_CODEX_WORK_DIR"] = str(work_dir)
        env["LGWF_FAKE_CODEX_SCENARIO_FILE"] = str(scenario_file)
        env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env, work_dir, log_file

    def _diagnostics(self, work_dir: Path, log_file: Path, final_status: dict[str, Any] | None = None) -> str:
        generated = sorted(str(path.relative_to(work_dir)).replace("\\", "/") for path in work_dir.rglob(".lgwf/*.json"))
        generated += sorted(str(path.relative_to(work_dir)).replace("\\", "/") for path in work_dir.rglob(".lgwf/*.jsonl"))
        missing = [path for path in [*OUTPUT_JSON_FILES, *PERSIST_FILES] if not (work_dir / path).exists()]
        log_tail = ""
        if log_file.exists():
            log_tail = log_file.read_text(encoding="utf-8", errors="replace")[-8000:]
        calls_tail = ""
        calls_path = work_dir / ".lgwf" / "fake_codex_calls.jsonl"
        if calls_path.exists():
            calls_tail = calls_path.read_text(encoding="utf-8")[-8000:]
        payload = {
            "final_status": final_status,
            "generated_artifacts": generated,
            "missing_artifacts": missing,
            "workflow_log_tail": log_tail,
            "fake_codex_calls_tail": calls_tail,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _status(self, *, session_id: str, work_dir: Path, env: dict[str, str], scenario_id: str, poll_index: int) -> dict[str, Any]:
        result = run_lgwf(
            ["status", "--work-dir", str(work_dir), "--session-id", session_id],
            env=env,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = parse_status_payload(result.stdout)
        trace_root = trace_dir(work_dir, scenario_id)
        write_json(trace_root / f"status_{poll_index:03d}.json", payload)
        write_json(
            trace_root / f"status_raw_{poll_index:03d}.json",
            {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
        )
        return payload

    def _approval_request_id(self, status_payload: dict[str, Any]) -> str | None:
        request_id = status_payload.get("human_request_id")
        if isinstance(request_id, str) and request_id:
            return request_id
        pending = status_payload.get("pending_human_requests")
        if isinstance(pending, list) and pending:
            first = pending[0]
            if isinstance(first, dict):
                candidate = first.get("request_id")
                if isinstance(candidate, str) and candidate:
                    return candidate
        return None

    def _approval_get(self, *, session_id: str, work_dir: Path, env: dict[str, str], scenario_id: str, index: int) -> dict[str, Any]:
        del session_id, env
        human_dir = work_dir / ".lgwf" / "human"
        requests = sorted(human_dir.glob("*.request.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        payload: dict[str, Any] | None = None
        for request_path in requests:
            request_id = request_path.name.removesuffix(".request.json")
            if not (human_dir / f"{request_id}.response.json").exists():
                payload = read_json(request_path)
                break
        self.assertIsNotNone(payload, f"未找到 pending approval request: {human_dir}")
        assert payload is not None
        write_json(trace_dir(work_dir, scenario_id) / f"approval_get_{index:02d}.json", payload)
        return payload

    def _approval_node_name(self, approval_payload: dict[str, Any]) -> str:
        for key in ("node_id", "current_node", "node"):
            value = approval_payload.get(key)
            if isinstance(value, str) and value in {"confirm_scope_if_needed", "confirm_delivery_or_revision"}:
                return value
        prompt = str(approval_payload.get("prompt") or approval_payload.get("message") or "")
        if "当前请求范围" in prompt:
            return "confirm_scope_if_needed"
        if "最终摘要草稿" in prompt:
            return "confirm_delivery_or_revision"
        self.fail(f"无法识别 approval 节点: {approval_payload}")
        raise AssertionError("unreachable")

    def _approval_id(self, approval_payload: dict[str, Any], request_id: str | None) -> str:
        for key in ("approval_id", "request_id", "id"):
            value = approval_payload.get(key)
            if isinstance(value, str) and value:
                return value
        if request_id:
            return request_id
        self.fail(f"approval 缺少 approval_id: {approval_payload}")
        raise AssertionError("unreachable")

    def _approval_submit(
        self,
        *,
        session_id: str,
        approval_id: str,
        submit_value: dict[str, Any],
        work_dir: Path,
        env: dict[str, str],
        scenario_id: str,
        index: int,
    ) -> None:
        trace_root = trace_dir(work_dir, scenario_id)
        value_file = trace_root / f"approval_submit_{index:02d}.json"
        write_json(value_file, submit_value)
        result = subprocess.run(
            [
                sys.executable,
                str(PACKAGE_ROOT.parent / "lgwf-wf-tools" / "workflows" / "wf-fix" / "scripts" / "safe_approval_submit.py"),
                "--work-dir",
                str(work_dir),
                "--request-id",
                approval_id,
                "--decision",
                "approve",
                "--value-file",
                str(value_file),
                "--comment",
                f"runtime fake approval {index}",
            ],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        response_payload: dict[str, Any]
        try:
            response_payload = parse_json_object(result.stdout)
        except AssertionError:
            response_payload = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        write_json(trace_root / f"approval_submit_result_{index:02d}.json", response_payload)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def _launch(self, scenario_id: str) -> tuple[ExitStack, dict[str, str], Path, Path, dict[str, Any]]:
        retryable_markers = ("PermissionError", "拒绝访问", ".pid.json")
        for attempt in range(1, 4):
            stack = ExitStack()
            env, work_dir, log_file = self._prepare_runtime(stack, scenario_id)
            case_input: dict[str, Any] = {
                "scenario_id": scenario_id,
                "repo_path": str(PACKAGE_ROOT.resolve()),
                "summary_scope": {
                    "baseline": "worktree git diff + latest commit",
                    "output_location": "chat markdown brief",
                },
            }
            if scenario_id == "scope_revise_then_approve":
                case_input["requested_extensions"] = ["请补充并确认仓库范围说明"]
            case_input_json = json.dumps(case_input, ensure_ascii=False)
            launch = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(WORKFLOW_LGWF),
                    "--work-dir",
                    str(work_dir),
                    "--input-json",
                    case_input_json,
                    "--background",
                ],
                env=env,
                timeout=30,
            )
            if launch.returncode == 0:
                payload = parse_json_object(launch.stdout, {"session_id"})
                return stack, env, work_dir, log_file, payload
            launch_text = launch.stderr + launch.stdout
            stack.close()
            if attempt == 3 or not any(marker in launch_text for marker in retryable_markers):
                self.fail(launch_text)
            time.sleep(1)
        self.fail("workflow 启动重试耗尽")
        raise AssertionError("unreachable")

    def _run_scenario(self, scenario_id: str) -> tuple[Path, dict[str, Any]]:
        scenario = scenario_payloads()[scenario_id]
        stack, env, work_dir, log_file, launch_payload = self._launch(scenario_id)
        self.addCleanup(stack.close)
        if os.environ.get("GIT_DIFF_BRIEF_RUNTIME_FAKE_KEEP_WORKDIR") == "1":
            self.addCleanup(lambda: None)

        session_id = str(launch_payload["session_id"])
        pid = launch_payload.get("pid")
        if isinstance(pid, int):
            self.addCleanup(lambda: run_lgwf(["stop", "--pid", str(pid)], env=env, timeout=30))

        approvals = list(scenario["approval_steps"])
        seen_approval_nodes: list[str] = []
        final_status: dict[str, Any] | None = None
        status_snapshots: list[dict[str, Any]] = []
        poll_index = 0
        same_waiting_node_count = 0
        last_waiting_node = ""
        seen_calls = 0
        deadline = time.monotonic() + 120
        first_approval_deadline = time.monotonic() + 20
        submit_deadline: float | None = None

        while time.monotonic() < deadline:
            poll_index += 1
            status_payload = self._status(
                session_id=session_id,
                work_dir=work_dir,
                env=env,
                scenario_id=scenario_id,
                poll_index=poll_index,
            )
            status_snapshots.append(status_payload)

            if is_terminal_status(status_payload):
                final_status = status_payload
                break

            calls_path = work_dir / ".lgwf" / "fake_codex_calls.jsonl"
            if calls_path.exists():
                seen_calls = len(calls_path.read_text(encoding="utf-8").splitlines())

            phase = str(status_payload.get("phase") or "")
            if phase in {"waiting_human", "waiting_review"}:
                approval_payload = self._approval_get(
                    session_id=session_id,
                    work_dir=work_dir,
                    env=env,
                    scenario_id=scenario_id,
                    index=len(seen_approval_nodes) + 1,
                )
                request_id = self._approval_request_id(status_payload)
                approval_id = self._approval_id(approval_payload, request_id)
                approval_node = self._approval_node_name(approval_payload)
                seen_approval_nodes.append(approval_node)

                if approval_node == last_waiting_node:
                    same_waiting_node_count += 1
                else:
                    same_waiting_node_count = 1
                    last_waiting_node = approval_node
                self.assertLessEqual(
                    same_waiting_node_count,
                    2 if scenario_id == "scope_revise_then_approve" and approval_node == "confirm_scope_if_needed" else 1,
                    self._diagnostics(work_dir, log_file, status_payload),
                )

                self.assertTrue(approvals, f"出现设计外 approval 节点: {approval_payload}")
                expected_step = approvals.pop(0)
                self.assertEqual(expected_step["approval_node"], approval_node, self._diagnostics(work_dir, log_file, status_payload))
                self._approval_submit(
                    session_id=session_id,
                    approval_id=approval_id,
                    submit_value=expected_step["submit_value"],
                    work_dir=work_dir,
                    env=env,
                    scenario_id=scenario_id,
                    index=len(seen_approval_nodes),
                )
                submit_deadline = time.monotonic() + 20
                time.sleep(1)
                continue

            if not seen_approval_nodes and time.monotonic() > first_approval_deadline and approvals:
                self.fail(f"首个 approval 超时未出现\n{self._diagnostics(work_dir, log_file, status_payload)}")

            if submit_deadline is not None and time.monotonic() > submit_deadline:
                self.fail(f"approval 提交后 20 秒内未推进\n{self._diagnostics(work_dir, log_file, status_payload)}")

            time.sleep(1)

        if final_status is None:
            self.fail(f"workflow 超时未收敛\n{self._diagnostics(work_dir, log_file)}")

        write_json(trace_dir(work_dir, scenario_id) / "final_status.json", final_status)
        self.assertFalse(approvals, f"仍有未消费 approval step: {approvals}")
        return work_dir, {
            "final_status": final_status,
            "status_snapshots": status_snapshots,
            "seen_approval_nodes": seen_approval_nodes,
            "session_id": session_id,
            "seen_calls": seen_calls,
        }

    def _assert_common_outputs(self, work_dir: Path) -> None:
        for relative_path in OUTPUT_JSON_FILES + PERSIST_FILES:
            self.assertTrue((work_dir / relative_path).exists(), relative_path)

        request_scope_capture = read_json(work_dir / ".lgwf/request_scope_capture.json")
        self.assertIn("repository_input_context", request_scope_capture)
        self.assertIn("summary_scope", request_scope_capture)
        self.assertIn("scope_confirmation_input", request_scope_capture)

        git_review = read_json(work_dir / ".lgwf/git_context_review.json")
        self.assertIn("passed", git_review)
        self.assertIn("issues", git_review)
        self.assertIn("summary", git_review)

        summary_context = read_json(work_dir / ".lgwf/change_summary_context.json")
        for key in (
            "change_overview",
            "key_files",
            "risk_points",
            "validation_candidates",
            "commit_message_suggestion",
            "commit_message_rationale",
        ):
            self.assertIn(key, summary_context)

        markdown_brief = read_json(work_dir / ".lgwf/change_brief_markdown.json")
        markdown = str(markdown_brief.get("change_brief_markdown", ""))
        self.assertTrue(markdown.startswith("# 变更摘要"))
        self.assertIn("git status --short", markdown)
        self.assertIn("git diff --stat", markdown)
        self.assertIn("git log -1 --stat", markdown)
        self.assertIsInstance(markdown_brief.get("sections"), list)

        delivery_context = read_json(work_dir / ".lgwf/delivery_review_context.json")
        for key in (
            "delivery_review_input",
            "final_change_brief_markdown",
            "summary_supporting_context",
            "commit_message_suggestion",
            "commit_message_rationale",
            "open_delivery_questions",
        ):
            self.assertIn(key, delivery_context)
        self.assertEqual(["none", "stage", "commit"], delivery_context["delivery_review_input"]["commit_action_options"])
        self.assertEqual("none", delivery_context["delivery_review_input"]["default_commit_action"])
        self.assertEqual(
            delivery_context["delivery_review_input"]["final_change_brief_markdown"],
            markdown,
        )
        selection_prompt = delivery_context["delivery_review_input"]["selection_prompt"]
        self.assertIn("本次变更摘要预览", selection_prompt)
        self.assertIn("请选择本次最终交付动作", selection_prompt)
        for option in (
            "1. 接受摘要",
            "2. 接受摘要，并执行 git add",
            "3. 接受摘要，执行 git add，并创建 commit",
            "4. 返回修订摘要",
            "5. 拒绝并终止 workflow",
        ):
            self.assertIn(option, selection_prompt)
        commit_plan = read_json(work_dir / ".lgwf/commit_plan.json")
        self.assertEqual("none", commit_plan["action"])
        commit_action_result = read_json(work_dir / ".lgwf/commit_action_result.json")
        self.assertTrue(commit_action_result["ok"])
        self.assertFalse(commit_action_result["executed"])

    def _read_calls(self, work_dir: Path) -> list[dict[str, Any]]:
        calls_path = work_dir / ".lgwf" / "fake_codex_calls.jsonl"
        self.assertTrue(calls_path.exists(), "缺少 fake_codex_calls.jsonl")
        return [
            json.loads(line)
            for line in calls_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _assert_no_unmapped_calls(self, calls: list[dict[str, Any]], work_dir: Path) -> None:
        self.assertFalse((work_dir / ".lgwf/fake_codex_unmatched.json").exists())
        self.assertFalse(any(bool(item.get("unmapped_call")) for item in calls))

    def _cleanup_kept_dir(self, work_dir: Path) -> None:
        if os.environ.get("GIT_DIFF_BRIEF_RUNTIME_FAKE_KEEP_WORKDIR") == "1":
            shutil.rmtree(work_dir.parent.parent, ignore_errors=True)

    def test_happy_path(self) -> None:
        work_dir, runtime = self._run_scenario("happy_path")
        self.addCleanup(self._cleanup_kept_dir, work_dir)

        self.assertEqual(runtime["final_status"].get("phase"), "completed", self._diagnostics(work_dir, work_dir.parent / "workflow.log", runtime["final_status"]))
        self.assertEqual(
            runtime["seen_approval_nodes"],
            ["confirm_scope_if_needed", "confirm_delivery_or_revision"],
        )
        self._assert_common_outputs(work_dir)

        scope_decision = read_json(work_dir / ".lgwf/request_scope_confirmation.json")
        delivery_decision = read_json(work_dir / ".lgwf/delivery_decision.json")
        self.assertEqual(scope_decision.get("approval", scope_decision.get("decision")), "approve")
        self.assertEqual(delivery_decision.get("approval", delivery_decision.get("decision")), "approve")
        self.assertEqual("none", delivery_decision.get("commit_action"))
        self.assertEqual("target_scope", delivery_decision.get("stage_scope"))

        calls = self._read_calls(work_dir)
        self.assertEqual([item["resolved_node_id"] for item in calls], EXPECTED_CALL_ORDER)
        self.assertEqual([item["call_index"] for item in calls], [1, 1, 1, 1])
        self._assert_no_unmapped_calls(calls, work_dir)

    def test_scope_revise_then_approve(self) -> None:
        work_dir, runtime = self._run_scenario("scope_revise_then_approve")
        self.addCleanup(self._cleanup_kept_dir, work_dir)

        self.assertEqual(runtime["final_status"].get("phase"), "completed", self._diagnostics(work_dir, work_dir.parent / "workflow.log", runtime["final_status"]))
        self.assertEqual(
            runtime["seen_approval_nodes"],
            [
                "confirm_scope_if_needed",
                "confirm_scope_if_needed",
                "confirm_delivery_or_revision",
            ],
        )
        self._assert_common_outputs(work_dir)

        scope_capture = read_json(work_dir / ".lgwf/request_scope_capture.json")
        self.assertFalse(scope_capture.get("needs_confirmation"))
        self.assertEqual(scope_capture.get("open_questions"), [])
        final_scope_decision = read_json(work_dir / ".lgwf/request_scope_confirmation.json")
        self.assertEqual(final_scope_decision.get("approval", final_scope_decision.get("decision")), "approve")
        delivery_decision = read_json(work_dir / ".lgwf/delivery_decision.json")
        self.assertEqual("none", delivery_decision.get("commit_action"))
        self.assertEqual("target_scope", delivery_decision.get("stage_scope"))
        first_submit = read_json(trace_dir(work_dir, "scope_revise_then_approve") / "approval_submit_01.json")
        self.assertEqual(first_submit.get("approval", first_submit.get("decision")), "revise")

        calls = self._read_calls(work_dir)
        self.assertEqual(
            [item["resolved_node_id"] for item in calls],
            EXPECTED_CALL_ORDER,
        )
        self.assertEqual([item["call_index"] for item in calls], [1, 1, 1, 1])
        self.assertEqual([item["resolved_node_id"] for item in calls].count("present_brief"), 1)
        self._assert_no_unmapped_calls(calls, work_dir)


if __name__ == "__main__":
    unittest.main()
