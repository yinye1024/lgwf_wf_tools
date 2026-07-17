from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
WF_CREATE_FAST_WORKFLOW_ROOT = PACKAGE_ROOT.parent / "wf-create-fast" / "wf"
LGWF_PY = (
    PACKAGE_ROOT.parent.parent
    / "vendor"
    / "lgwf-client-assist"
    / "scripts"
    / "lgwf.py"
)
SAFE_APPROVAL_SUBMIT = PACKAGE_ROOT.parent / "wf-fix" / "scripts" / "safe_approval_submit.py"
STATUS_TIMEOUT_SECONDS = 120
WAITING_HUMAN_TIMEOUT_SECONDS = 15
PHASE_POLL_INTERVAL_SECONDS = 1
RUNTIME_TRACE_DIRNAME = ".lgwf-test"


def write_utf8_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_utf8_json(path: Path) -> Any:
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
    expected = f" with keys {sorted(required_keys)}" if required_keys else ""
    raise AssertionError(f"stdout 未包含 JSON object{expected}:\n{text}")


def build_sample_prompt_workflow(root: Path) -> Path:
    source_root = root / "sample_prompt_workflow"
    (source_root / "flow" / "agents").mkdir(parents=True)
    (source_root / "README.md").write_text("# sample prompt workflow\n", encoding="utf-8")
    (source_root / "flow" / "workflow.lgwf").write_text("WORKFLOW prompt_demo;\n", encoding="utf-8")
    (source_root / "flow" / "agents" / "inspect.md").write_text(
        "# inspect\n\n分析源流程职责与输入输出约束。\n",
        encoding="utf-8",
    )
    return source_root


def build_runtime_authoring_package(root: Path) -> Path:
    mirror_root = root / "workflow_repo_mirror"
    if mirror_root.exists():
        shutil.rmtree(mirror_root)
    workflows_root = mirror_root / "workflows"
    package_root = workflows_root / "wf-convert"
    child_target = workflows_root / "wf-create-fast"
    ignore = shutil.ignore_patterns("ws", ".lgwf", "__pycache__", "*.pyc", "*.pyo")
    shutil.copytree(PACKAGE_ROOT, package_root, ignore=ignore)
    shutil.copytree(WF_CREATE_FAST_WORKFLOW_ROOT.parent, child_target, ignore=ignore)
    return package_root / "wf" / "workflow.lgwf"


def write_prompt_file_mode_patch(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "sitecustomize.py").write_text(
        textwrap.dedent(
            r"""
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

            """
        ).lstrip(),
        encoding="utf-8",
    )


def build_fake_runner_script(path: Path) -> None:
    script = textwrap.dedent(
        r"""
        from __future__ import annotations

        import argparse
        import json
        import os
        import sys
        from pathlib import Path


        def extract_main_prompt_path(prompt_text: str) -> str:
            lines = prompt_text.splitlines()
            for index, line in enumerate(lines[:-1]):
                if line.strip() == "Main prompt file:":
                    return lines[index + 1].strip().replace("\\", "/")
            return ""


        def load_prompt_key(prompt_file: str) -> str:
            prompt_path = Path(prompt_file)
            metadata_path = prompt_path.parent / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    metadata = {}
                main_prompt_path = str(metadata.get("main_prompt_path") or "")
                if main_prompt_path:
                    marker = "/wf/"
                    normalized = main_prompt_path.replace("\\", "/")
                    snapshot_marker = "/.lgwf/workflow/"
                    if snapshot_marker in normalized:
                        return "wf/" + normalized.split(snapshot_marker, 1)[1]
                    if marker in normalized:
                        return "wf/" + normalized.split(marker, 1)[1]
                    if normalized.startswith("wf/"):
                        return normalized
            prompt_text = prompt_path.read_text(encoding="utf-8")
            main_prompt_path = extract_main_prompt_path(prompt_text)
            normalized = main_prompt_path.replace("\\", "/")
            marker = "/wf/"
            snapshot_marker = "/.lgwf/workflow/"
            if snapshot_marker in normalized:
                return "wf/" + normalized.split(snapshot_marker, 1)[1]
            if marker in normalized:
                return "wf/" + normalized.split(marker, 1)[1]
            if normalized.startswith("wf/"):
                return normalized
            return normalized or prompt_file.replace("\\", "/")


        def extract_output_path(prompt_file: str) -> str:
            prompt_text = Path(prompt_file).read_text(encoding="utf-8")
            for line in prompt_text.splitlines():
                stripped = line.strip()
                marker = "Output path:"
                if marker in stripped:
                    return stripped.split(marker, 1)[1].strip()
            return ""


        def main() -> int:
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument("--prompt-file")
            parser.add_argument("--mapping-file")
            parser.add_argument("--call-log")
            parser.add_argument("prompt", nargs="?")
            args, unknown = parser.parse_known_args()

            mapping_file = Path(args.mapping_file or os.environ["LGWF_FAKE_CODEX_MAPPING_FILE"])
            call_log_path = Path(args.call_log or os.environ["LGWF_FAKE_CODEX_CALL_LOG"])
            mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
            call_log_path.parent.mkdir(parents=True, exist_ok=True)
            existing = []
            if call_log_path.exists():
                existing = json.loads(call_log_path.read_text(encoding="utf-8"))

            prompt_file = args.prompt_file
            if not prompt_file:
                candidates = [str(args.prompt or ""), *[str(item) for item in unknown]]
                prompt_text = next((item for item in candidates if "# LGWF Codex Handoff" in item), "")
                if not prompt_text and "-" in candidates:
                    prompt_text = sys.stdin.read()
                if not prompt_text:
                    prompt_text = next((item for item in reversed(candidates) if item and not item.startswith("-")), "")
                prompt_path = call_log_path.parent / f"inline_prompt_{len(existing) + 1}.txt"
                prompt_path.write_text(prompt_text, encoding="utf-8")
                prompt_file = str(prompt_path)

            prompt_key = load_prompt_key(prompt_file)
            call_index = 1 + sum(1 for item in existing if item.get("prompt_key") == prompt_key)
            scenario_mapping = mapping.get("responses", {})
            prompt_responses = scenario_mapping.get(prompt_key, [])
            response = next((item for item in prompt_responses if item.get("call_index") == call_index), None)
            if response is None:
                payload = {
                    "error": "fake-codex-fallback",
                    "prompt_file": prompt_file,
                    "prompt_key": prompt_key,
                    "call_index": call_index,
                    "known_mapping_keys": sorted(scenario_mapping.keys()),
                    "unknown_args": unknown,
                }
                existing.append(
                    {
                        "prompt_file": prompt_file,
                        "prompt_key": prompt_key,
                        "call_index": call_index,
                        "matched": False,
                        "output_summary": payload["error"],
                    }
                )
                call_log_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps(payload, ensure_ascii=False))
                return 2

            existing.append(
                {
                    "prompt_file": prompt_file,
                    "prompt_key": prompt_key,
                    "call_index": call_index,
                    "matched": True,
                    "output_summary": response.get("summary", ""),
                    "unknown_args": unknown,
                }
            )
            call_log_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            output_path = extract_output_path(prompt_file)
            if output_path:
                target = Path(output_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(response["payload"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(response["payload"], ensure_ascii=False))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
        """
    ).strip()
    path.write_text(script + "\n", encoding="utf-8")


def write_fake_codex_bundle(fake_root: Path) -> Path:
    fake_root.mkdir(parents=True, exist_ok=True)
    fake_script = fake_root / "fake_codex.py"
    build_fake_runner_script(fake_script)
    for name in ("codex.cmd", "codex.bat"):
        (fake_root / name).write_text('@echo off\r\npython "%~dp0fake_codex.py" %*\r\n', encoding="utf-8")
    return fake_script


class RuntimeTrace:
    def __init__(self, root: Path) -> None:
        self.root = root / RUNTIME_TRACE_DIRNAME
        self.root.mkdir(parents=True, exist_ok=True)
        self.status_log = self.root / "status_trace.jsonl"
        self.command_log = self.root / "command_trace.jsonl"
        self.approval_log = self.root / "approval_trace.jsonl"

    def record(self, path: Path, payload: Any) -> None:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


class WorkflowRuntimeHarness:
    def __init__(self, *, work_dir: Path, scenario: dict[str, Any], workflow_lgwf: Path = WORKFLOW_LGWF) -> None:
        self.work_dir = work_dir
        self.scenario = scenario
        self.workflow_lgwf = workflow_lgwf
        self.trace = RuntimeTrace(work_dir)
        self.runtime_env = os.environ.copy()
        self.fake_root = work_dir / "fake_codex"
        self.patch_root = work_dir / "pythonpath"
        self.fake_root.mkdir(parents=True, exist_ok=True)
        self.patch_root.mkdir(parents=True, exist_ok=True)
        self.mapping_file = self.fake_root / "mapping.json"
        self.call_log = self.fake_root / "call_log.json"
        self.fake_script = write_fake_codex_bundle(self.fake_root)
        write_prompt_file_mode_patch(self.patch_root)
        write_utf8_json(self.mapping_file, {"responses": self._build_responses()})
        self.runtime_env["PATH"] = str(self.fake_root) + os.pathsep + self.runtime_env.get("PATH", "")
        self.runtime_env["PYTHONPATH"] = str(self.patch_root) + os.pathsep + self.runtime_env.get("PYTHONPATH", "")
        self.runtime_env["LGWF_FAKE_CODEX_WORK_DIR"] = str(self.work_dir)
        self.runtime_env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
        self.runtime_env["LGWF_FAKE_CODEX_MAPPING_FILE"] = str(self.mapping_file)
        self.runtime_env["LGWF_FAKE_CODEX_CALL_LOG"] = str(self.call_log)

    def _build_responses(self) -> dict[str, list[dict[str, Any]]]:
        workflow_root = "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow"
        source_root = "<temp_fixture_root>/sample_prompt_workflow"
        inspection_stage = {
            "stage_id": "discover",
            "name": "发现源 workflow",
            "responsibility": "索引源 prompt workflow 的入口、说明和 agent prompt",
            "inputs": ["prompt workflow 目录"],
            "outputs": ["源文件索引和职责摘要"],
            "source_files": ["README.md", "flow/workflow.lgwf"],
            "evidence_strength": "high",
            "proposal_consumer": ["raw_intent", "stages"],
            "degrade_target": "none",
            "evidence_summary": "README 与 workflow.lgwf 明确给出源 workflow 入口",
        }
        inspection_prompt_contract = {
            "prompt_path": "flow/agents/inspect.md",
            "responsibility": "分析源流程职责与输入输出约束",
            "inputs": ["源 workflow 文件"],
            "outputs": ["职责与契约摘要"],
            "constraints": ["不修改源目录"],
            "source_files": ["flow/agents/inspect.md"],
            "evidence_strength": "high",
            "proposal_consumer": ["prompt_contracts"],
            "degrade_target": "none",
            "evidence_summary": "inspect.md 明确声明分析职责与输入输出约束",
        }
        source_business_contract = {
            "goal": "分析源 prompt workflow 并整理创建输入",
            "inputs": [],
            "outputs": [],
            "stages": [
                {
                    "rule_id": "stage_rule_001",
                    "statement": "必须先索引源 workflow，再整理创建输入",
                    "source_files": ["README.md", "flow/workflow.lgwf"],
                    "evidence_strength": "high",
                }
            ],
            "decision_rules": [],
            "approval_points": [],
            "error_paths": [],
            "invariants": [],
        }
        conversion_mapping = [
            {
                "mapping_id": "mapping_001",
                "source_rule_ids": ["stage_rule_001"],
                "mapping_type": "convert_to_lgwf_node",
                "target_design": "索引与分析节点",
                "rationale": "保留先索引后分析的业务顺序",
            }
        ]
        parity_requirements = [
            {
                "requirement_id": "parity_001",
                "source_rule_ids": ["stage_rule_001"],
                "description": "保持先索引后分析的顺序",
                "verification": "检查目标 workflow 的节点顺序",
            }
        ]
        proposal_stage = {
            "stage_id": "discover",
            "name": "发现源 workflow",
            "responsibility": "索引源 prompt workflow 的入口、说明和 agent prompt",
            "inputs": ["prompt workflow 目录"],
            "outputs": ["源文件索引和职责摘要"],
            "source_files": ["README.md", "flow/workflow.lgwf"],
            "evidence_strength": "high",
            "evidence_summary": "README 与 workflow.lgwf 明确给出源 workflow 入口",
        }
        proposal_prompt_contract = {
            "prompt_path": "flow/agents/inspect.md",
            "responsibility": "分析源流程职责与输入输出约束",
            "inputs": ["源 workflow 文件"],
            "outputs": ["职责与契约摘要"],
            "constraints": ["不修改源目录"],
            "source_files": ["flow/agents/inspect.md"],
            "evidence_strength": "high",
            "evidence_summary": "inspect.md 明确声明分析职责与输入输出约束",
        }
        happy_confirmed = {
            "workflow_name": "demo-converted-workflow",
            "target_package_root": workflow_root,
            "raw_intent": "把现有 prompt workflow 转成 LGWF workflow，并输出可交给 wf-create-fast 的完整 handoff target。",
            "source_root": source_root,
            "stages": [proposal_stage],
            "prompt_contracts": [proposal_prompt_contract],
            "source_business_contract": source_business_contract,
            "prompt_execution_mechanics": [],
            "presentation_constraints": [],
            "discarded_prompt_techniques": [],
            "conversion_mapping": conversion_mapping,
            "parity_requirements": parity_requirements,
            "human_approval_points": ["confirm_create_input"],
            "assumptions": ["源目录文本文件均可按 UTF-8 读取"],
            "out_of_scope": ["不直接生成最终 workflow package"],
            "run_workflow_notes_for_wf_create_fast": ["用户确认后 handoff 给主 agent 启动 wf-create-fast"],
        }
        revise_confirmed = {
            "workflow_name": "demo-converted-workflow",
            "target_package_root": workflow_root,
            "raw_intent": "把现有 prompt workflow 转成可交给 wf-create-fast 的完整 handoff target；本 workflow 负责分析、proposal、人工确认，并在确认后 handoff 给主 agent 启动 wf-create-fast。",
            "source_root": source_root,
            "stages": [proposal_stage],
            "prompt_contracts": [proposal_prompt_contract],
            "source_business_contract": source_business_contract,
            "prompt_execution_mechanics": [],
            "presentation_constraints": [],
            "discarded_prompt_techniques": [],
            "conversion_mapping": conversion_mapping,
            "parity_requirements": parity_requirements,
            "human_approval_points": ["confirm_create_input"],
            "assumptions": ["样例源目录只覆盖文本文件索引与转换输入整理，不覆盖真实业务 happy path"],
            "out_of_scope": ["不直接生成最终 workflow package"],
            "run_workflow_notes_for_wf_create_fast": [
                "requires_main_agent_confirmation=true",
                "用户确认后由主 agent 启动 wf-create-fast",
            ],
        }
        inspection_payload = {
            "analysis_plan": [
                {"goal": "识别业务阶段", "method": "读取入口和 workflow 文件", "expected_evidence": "阶段职责"}
            ],
            "issue_resolution_plan": [],
            "priority_files": [
                {"path": "README.md", "reason": "入口说明", "expected_signal": "阶段与约束"}
            ],
            "gap_checks": ["缺少外部资源引用", "缺少输入输出说明"],
            "known_limits": ["样例目录不覆盖真实业务 happy path"],
        }
        inspection_result = {
            "source_summary": [
                {"path": "README.md", "role": "入口说明", "evidence": "说明这是 sample prompt workflow"},
                {"path": "flow/workflow.lgwf", "role": "workflow 入口", "evidence": "声明 WORKFLOW prompt_demo"},
                {"path": "flow/agents/inspect.md", "role": "分析 prompt", "evidence": "声明分析职责与输入输出约束"},
            ],
            "detected_stages": [inspection_stage],
            "prompt_contracts": [inspection_prompt_contract],
            "source_business_contract": source_business_contract,
            "prompt_execution_mechanics": [],
            "presentation_constraints": [],
            "discarded_prompt_techniques": [],
            "human_approval_points": [],
            "gaps": [],
            "risks": [],
            "assumptions": ["样例目录不覆盖真实业务 happy path"],
        }
        proposal_first = {
            "workflow_name": "demo-converted-workflow",
            "target_package_root": workflow_root,
            "raw_intent": "把现有 prompt workflow 转成 LGWF workflow，并输出可交给 wf-create-fast 的完整 handoff target。",
            "source_root": source_root,
            "stages": [proposal_stage],
            "prompt_contracts": happy_confirmed["prompt_contracts"],
            "source_business_contract": happy_confirmed["source_business_contract"],
            "prompt_execution_mechanics": happy_confirmed["prompt_execution_mechanics"],
            "presentation_constraints": happy_confirmed["presentation_constraints"],
            "discarded_prompt_techniques": happy_confirmed["discarded_prompt_techniques"],
            "conversion_mapping": happy_confirmed["conversion_mapping"],
            "parity_requirements": happy_confirmed["parity_requirements"],
            "human_approval_points": ["confirm_create_input"],
            "assumptions": ["源目录文本文件均可按 UTF-8 读取"],
            "out_of_scope": ["不直接生成最终 workflow package"],
            "run_workflow_notes_for_wf_create_fast": ["用户确认后 handoff 给主 agent 启动 wf-create-fast"],
        }
        proposal_second = {
            "workflow_name": "demo-converted-workflow",
            "target_package_root": workflow_root,
            "raw_intent": revise_confirmed["raw_intent"],
            "source_root": source_root,
            "stages": revise_confirmed["stages"],
            "prompt_contracts": revise_confirmed["prompt_contracts"],
            "source_business_contract": revise_confirmed["source_business_contract"],
            "prompt_execution_mechanics": revise_confirmed["prompt_execution_mechanics"],
            "presentation_constraints": revise_confirmed["presentation_constraints"],
            "discarded_prompt_techniques": revise_confirmed["discarded_prompt_techniques"],
            "conversion_mapping": revise_confirmed["conversion_mapping"],
            "parity_requirements": revise_confirmed["parity_requirements"],
            "human_approval_points": ["confirm_create_input"],
            "assumptions": revise_confirmed["assumptions"],
            "out_of_scope": revise_confirmed["out_of_scope"],
            "run_workflow_notes_for_wf_create_fast": revise_confirmed["run_workflow_notes_for_wf_create_fast"],
        }
        proposal_with_evidence = dict(proposal_second)
        propose_reason_first = {
            "proposal_plan": [{"field": "raw_intent", "source": "inspection + target approval"}],
            "issue_resolution_plan": [],
            "fields_to_include": list(proposal_first.keys()),
            "field_sources": {"raw_intent": "inspection + target approval"},
            "assumption_policy": "缺失值只做最小补全，不扩展 scope",
            "known_limits": ["确认前不 handoff 给主 agent"],
        }
        propose_reason_second = {
            "proposal_plan": [{"field": "raw_intent", "source": "approval revise changes"}],
            "issue_resolution_plan": [],
            "fields_to_include": list(proposal_second.keys()),
            "field_sources": {"raw_intent": "approval revise changes"},
            "assumption_policy": "修订优先覆盖 approval changes",
            "known_limits": ["仍只生成 wf-create-fast handoff 输入描述"],
        }
        propose_reason_observe_fix = {
            "proposal_plan": [{"field": "stages", "source": "previous proposal + observe issue"}],
            "issue_resolution_plan": [
                {
                    "field": "stages",
                    "blocking": True,
                    "required_change": "为每个 stage 补充 evidence_strength",
                    "resolution": "已在 stage 条目中补充 high confidence 证据说明",
                }
            ],
            "fields_to_include": list(proposal_with_evidence.keys()),
            "assumption_policy": "证据不足时降级到 assumptions",
            "known_limits": [],
        }
        inspection_semantic_pass = {
            "schema_version": 1,
            "stage": "inspection",
            "observer": "codex",
            "issues": [],
        }
        proposal_semantic_pass = {
            "schema_version": 1,
            "stage": "proposal",
            "observer": "codex",
            "issues": [],
        }
        proposal_semantic_revise = {
            "schema_version": 1,
            "stage": "proposal",
            "observer": "codex",
            "issues": [
                {
                    "observer": "codex",
                    "code": "APPROVAL_NOT_REUSABLE",
                    "field": "stages",
                    "blocking": True,
                    "severity": "high",
                    "issue": "stage 证据摘要不足，approval 无法原样确认",
                    "required_change": "补充可供 approval 判断的 stage 证据说明",
                }
            ],
        }
        mapping = {
            "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/reason.md": [
                {"call_index": 1, "payload": inspection_payload, "summary": "inspection reason"},
            ],
            "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/act.md": [
                {"call_index": 1, "payload": inspection_result, "summary": "inspection act"},
            ],
            "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/observe.md": [
                {"call_index": 1, "payload": inspection_semantic_pass, "summary": "inspection semantic observe"},
            ],
        }
        if self.scenario["scenario_id"] == "happy_path":
            mapping.update(
                {
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/reason.md": [
                        {"call_index": 1, "payload": propose_reason_first, "summary": "proposal reason 1"},
                    ],
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": [
                        {"call_index": 1, "payload": proposal_first, "summary": "proposal act 1"},
                    ],
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": [
                        {
                            "call_index": 1,
                            "payload": proposal_semantic_pass,
                            "summary": "proposal semantic observe 1",
                        },
                    ],
                }
            )
        elif self.scenario["scenario_id"] == "observe_revise_then_pass":
            mapping.update(
                {
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/reason.md": [
                        {"call_index": 1, "payload": propose_reason_first, "summary": "proposal reason 1"},
                        {"call_index": 2, "payload": propose_reason_observe_fix, "summary": "proposal reason 2"},
                    ],
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": [
                        {"call_index": 1, "payload": proposal_first, "summary": "proposal act 1"},
                        {"call_index": 2, "payload": proposal_with_evidence, "summary": "proposal act 2"},
                    ],
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": [
                        {
                            "call_index": 1,
                            "payload": proposal_semantic_revise,
                            "summary": "proposal semantic observe 1",
                        },
                        {
                            "call_index": 2,
                            "payload": proposal_semantic_pass,
                            "summary": "proposal semantic observe 2",
                        },
                    ],
                }
            )
        else:
            mapping.update(
                {
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/reason.md": [
                        {"call_index": 1, "payload": propose_reason_first, "summary": "proposal reason 1"},
                        {"call_index": 2, "payload": propose_reason_second, "summary": "proposal reason 2"},
                    ],
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": [
                        {"call_index": 1, "payload": proposal_first, "summary": "proposal act 1"},
                        {"call_index": 2, "payload": proposal_second, "summary": "proposal act 2"},
                    ],
                    "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": [
                        {
                            "call_index": 1,
                            "payload": proposal_semantic_pass,
                            "summary": "proposal semantic observe 1",
                        },
                        {
                            "call_index": 2,
                            "payload": proposal_semantic_pass,
                            "summary": "proposal semantic observe 2",
                        },
                    ],
                }
            )
        return mapping

    def _run_cli(self, *args: str, expect_json: bool = True) -> Any:
        command = [sys.executable, str(LGWF_PY), *args]
        resolved_command = self.resolve_cli_command(command)
        command_record: dict[str, Any] = {"command": command}
        if resolved_command != command:
            command_record["resolved_command"] = resolved_command
        self.trace.record(self.trace.command_log, command_record)
        completed = subprocess.run(
            resolved_command,
            cwd=str(self.workflow_lgwf.parent),
            env=self.runtime_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.trace.record(
            self.trace.command_log,
            {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"命令失败: {' '.join(command)}\n"
                f"RESOLVED:\n{' '.join(resolved_command)}\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        if not expect_json:
            return completed.stdout
        try:
            return parse_json_object(completed.stdout)
        except AssertionError as exc:
            raise AssertionError(f"命令未返回可解析 JSON: {' '.join(command)}\n{completed.stdout}") from exc

    def resolve_cli_command(self, command: list[str]) -> list[str]:
        if "--input-json-file" not in command:
            return command
        index = command.index("--input-json-file")
        if index + 1 >= len(command):
            raise AssertionError(f"--input-json-file 缺少路径: {command}")
        input_path = Path(command[index + 1])
        input_payload = input_path.read_text(encoding="utf-8")
        return [*command[:index], "--input-json", input_payload, *command[index + 2 :]]

    def start(self, *, input_json_path: Path) -> str:
        runtime_input_path = self.work_dir / RUNTIME_TRACE_DIRNAME / "runtime_input.json"
        runtime_input_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_json_path, runtime_input_path)
        command = [
            "run",
            "--workflow-lgwf",
            str(self.workflow_lgwf),
            "--work-dir",
            str(self.work_dir),
            "--input-json-file",
            str(runtime_input_path),
            "--background",
        ]
        if self.should_use_rerun_existing():
            command.append("--rerun-existing")
        payload = self._run_cli(*command)
        session_id = str(payload.get("session_id") or payload.get("session-id") or "")
        if not session_id:
            raise AssertionError(f"run 输出缺少 session_id: {payload}")
        return session_id

    def should_use_rerun_existing(self) -> bool:
        if not self.scenario.get("rerun_existing"):
            return False
        lgwf_root = self.work_dir / ".lgwf"
        if not lgwf_root.exists() or not lgwf_root.is_dir():
            return False
        return any(lgwf_root.iterdir())

    def status(self, session_id: str) -> dict[str, Any]:
        payload = self._run_cli("status", "--work-dir", str(self.work_dir), "--session-id", session_id)
        if not isinstance(payload, dict):
            raise AssertionError(f"status 输出不是 JSON object: {payload}")
        phase = payload.get("phase") or payload.get("status")
        if not phase:
            raise AssertionError(f"status 输出缺少 phase/status: {payload}")
        self.trace.record(self.trace.status_log, payload)
        return payload

    def approval_get(self, request_id: str) -> dict[str, Any]:
        payload = self._run_cli("approval", "get", "--work-dir", str(self.work_dir), "--request-id", request_id)
        if not isinstance(payload, dict):
            raise AssertionError(f"approval get 输出不是 JSON object: {payload}")
        self.trace.record(self.trace.approval_log, {"action": "get", "payload": payload})
        return payload

    def approval_submit(self, request_id: str, *, decision: str, value_json_path: Path) -> dict[str, Any]:
        command = [
            sys.executable,
            str(SAFE_APPROVAL_SUBMIT),
            "--work-dir",
            str(self.work_dir),
            "--request-id",
            request_id,
            "--decision",
            decision,
            "--comment",
            "runtime fake e2e auto approval",
        ]
        if decision != "approve":
            command.extend(["--value-file", str(value_json_path)])
        self.trace.record(self.trace.command_log, {"command": command})
        completed = subprocess.run(
            command,
            cwd=str(self.workflow_lgwf.parent),
            env=self.runtime_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.trace.record(
            self.trace.command_log,
            {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
        if completed.returncode != 0:
            raise AssertionError(f"命令失败: {' '.join(command)}\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")
        payload = parse_json_object(completed.stdout)
        if not isinstance(payload, dict):
            raise AssertionError(f"approval submit 输出不是 JSON object: {payload}")
        self.trace.record(
            self.trace.approval_log,
            {
                "action": "submit",
                "request_id": request_id,
                "decision": decision,
                "value_json_path": str(value_json_path),
                "payload": payload,
            },
        )
        return payload

    def review_submit(self, request_id: str, *, route: str, value_json_path: Path) -> dict[str, Any]:
        command = [
            "review",
            "submit",
            "--work-dir",
            str(self.work_dir),
            "--request-id",
            request_id,
            "--route",
            route,
        ]
        if route != "approve":
            value_json = json.dumps(read_utf8_json(value_json_path), ensure_ascii=False)
            command.extend(["--value-json", value_json])
        command.extend(
            [
                "--comment",
                "runtime fake e2e auto review",
            ]
        )
        payload = self._run_cli(
            *command,
        )
        if not isinstance(payload, dict):
            raise AssertionError(f"review submit 输出不是 JSON object: {payload}")
        self.trace.record(
            self.trace.approval_log,
            {
                "action": "review_submit",
                "request_id": request_id,
                "route": route,
                "value_json_path": str(value_json_path),
                "payload": payload,
            },
        )
        return payload


class RuntimeFakeE2ETests(unittest.TestCase):
    maxDiff = None

    def run_scenario(
        self,
        scenario: dict[str, Any],
    ) -> tuple[Path, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        temp_dir = Path(tempfile.mkdtemp(prefix=f"wf-convert-{scenario['scenario_id']}-"))
        if os.environ.get("LGWF_TEST_CLEANUP_TEMP") == "1":
            self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        fixture_root = build_sample_prompt_workflow(temp_dir)
        workflow_lgwf = build_runtime_authoring_package(temp_dir)
        work_dir = temp_dir / "runtime"
        work_dir.mkdir(parents=True, exist_ok=True)
        harness = WorkflowRuntimeHarness(work_dir=work_dir, scenario=scenario, workflow_lgwf=workflow_lgwf)
        input_json_path = temp_dir / "input.json"
        write_utf8_json(
            input_json_path,
            {
                "prompt_convert_target": {
                    "target_dir": str(fixture_root),
                    "entry_files": ["README.md", "flow/workflow.lgwf"],
                    "target_workflow_name": "demo-converted-workflow",
                    "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                    "constraints": ["不直接生成最终 LGWF workflow", "不自动调用 wf-create-fast"],
                }
            },
        )
        session_id = harness.start(input_json_path=input_json_path)
        phase_history: list[dict[str, Any]] = []
        approval_events: list[dict[str, Any]] = []
        scenario_steps = list(scenario["approval_steps"])
        approval_counts: dict[str, int] = {}
        start_time = time.time()

        while time.time() - start_time < STATUS_TIMEOUT_SECONDS:
            status_payload = harness.status(session_id)
            phase = str(status_payload.get("phase") or status_payload.get("status"))
            current_node = status_payload.get("current_node") or status_payload.get("pending_action")
            phase_history.append({"phase": phase, "current_node": current_node})
            if phase == "completed":
                break
            if phase in {"failed", "stopped"}:
                raise AssertionError(f"workflow 终态失败: {status_payload}")
            if self.has_handoff_pending(work_dir):
                if scenario_steps:
                    raise AssertionError(f"handoff 已 pending，但仍有未消费 approval 步骤: {scenario_steps}")
                phase_history.append({"phase": "waiting_handoff", "current_node": "handoff_to_wf_create_fast"})
                break
            if phase in {"waiting_human", "waiting_review"}:
                request_id = self.extract_request_id(status_payload)
                if phase == "waiting_human":
                    approval_payload = harness.approval_get(request_id)
                    node_id = self.extract_approval_node_id(
                        approval_payload,
                        fallback=status_payload.get("current_node"),
                    )
                else:
                    approval_payload = status_payload.get("pending_action") or status_payload
                    node_id = str(status_payload.get("current_node") or self.extract_approval_node_id(approval_payload))
                approval_counts[node_id] = approval_counts.get(node_id, 0) + 1
                if approval_counts[node_id] > 2:
                    raise AssertionError(f"approval 节点超出预期等待次数: {node_id}")
                if not scenario_steps:
                    raise AssertionError(f"无剩余 approval 计划，但 runtime 请求了: {node_id}")
                step = scenario_steps.pop(0)
                self.assertEqual(step["approval_node"], node_id)
                approval_events.append(
                    {
                        "node_id": node_id,
                        "request_id": request_id,
                        "count": approval_counts[node_id],
                        "decision": self.business_decision(step),
                    }
                )
                submit_value = self.materialize_submit_value(step["submit_value"], fixture_root)
                submit_path = temp_dir / f"{node_id}-{approval_counts[node_id]}.json"
                write_utf8_json(submit_path, submit_value)
                if phase == "waiting_human":
                    harness.approval_submit(
                        request_id,
                        decision=self.controller_decision(step),
                        value_json_path=submit_path,
                    )
                else:
                    harness.review_submit(
                        request_id,
                        route=self.business_decision(step),
                        value_json_path=submit_path,
                    )
                self.wait_for_phase_change(
                    harness=harness,
                    session_id=session_id,
                    previous_phase=phase,
                    previous_node=node_id,
                    previous_request_id=request_id,
                )
                continue
            time.sleep(PHASE_POLL_INTERVAL_SECONDS)
        else:
            raise AssertionError(
                f"场景超时未完成: {scenario['scenario_id']}; 最近状态={phase_history[-1] if phase_history else '<none>'}"
            )

        if scenario_steps:
            raise AssertionError(f"仍有未消费 approval 步骤: {scenario_steps}")
        call_log = read_utf8_json(harness.call_log)
        return work_dir, phase_history, call_log, approval_events

    def has_handoff_pending(self, work_dir: Path) -> bool:
        handoff_dir = work_dir / ".lgwf" / "handoff"
        return handoff_dir.is_dir() and any(handoff_dir.glob("*.pending.json"))

    def wait_for_phase_change(
        self,
        *,
        harness: WorkflowRuntimeHarness,
        session_id: str,
        previous_phase: str,
        previous_node: str,
        previous_request_id: str,
    ) -> None:
        deadline = time.time() + WAITING_HUMAN_TIMEOUT_SECONDS
        last_status: dict[str, Any] | None = None
        while time.time() < deadline:
            status_payload = harness.status(session_id)
            last_status = status_payload
            phase = str(status_payload.get("phase") or status_payload.get("status"))
            node = status_payload.get("current_node") or status_payload.get("pending_action")
            request_id = self.extract_request_id(status_payload, required=False)
            if phase != previous_phase or node != previous_node or request_id != previous_request_id:
                return
            time.sleep(PHASE_POLL_INTERVAL_SECONDS)
        raise AssertionError(
            f"approval submit 后流程未前进: node={previous_node}, request_id={previous_request_id}, last_status={last_status}"
        )

    def extract_request_id(self, status_payload: dict[str, Any], *, required: bool = True) -> str:
        request_id = status_payload.get("human_request_id")
        if request_id:
            return str(request_id)
        pending = status_payload.get("pending_human_requests") or []
        if isinstance(pending, list) and pending:
            candidate = pending[0].get("request_id")
            if candidate:
                return str(candidate)
        pending_action = status_payload.get("pending_action")
        if isinstance(pending_action, dict):
            candidate = pending_action.get("request_id") or pending_action.get("child_request_id")
            if candidate:
                return str(candidate)
        if required:
            raise AssertionError(f"waiting_human 状态缺少 request_id: {status_payload}")
        return ""

    def controller_decision(self, step: dict[str, Any]) -> str:
        decision = str(
            step.get("decision")
            or step.get("submit_value", {}).get("approval")
            or step.get("submit_value", {}).get("decision")
            or "approve"
        )
        if decision == "reject":
            return "reject"
        return "approve"

    def business_decision(self, step: dict[str, Any]) -> str:
        return str(
            step.get("submit_value", {}).get("approval")
            or step.get("submit_value", {}).get("decision")
            or step.get("decision")
            or "approve"
        )

    def extract_approval_node_id(self, approval_payload: dict[str, Any], *, fallback: Any = None) -> str:
        for key in ("node_id", "approval_node", "current_node"):
            value = approval_payload.get(key)
            if value:
                return str(value)
        request = approval_payload.get("approval") or approval_payload.get("request") or {}
        if isinstance(request, dict):
            for key in ("node_id", "approval_node", "current_node"):
                value = request.get(key)
                if value:
                    return str(value)
        if fallback:
            return str(fallback)
        raise AssertionError(f"approval get 输出缺少 node id: {approval_payload}")

    def materialize_submit_value(self, payload: Any, fixture_root: Path) -> Any:
        if isinstance(payload, dict):
            return {key: self.materialize_submit_value(value, fixture_root) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self.materialize_submit_value(item, fixture_root) for item in payload]
        if isinstance(payload, str):
            return payload.replace("<temp_fixture_root>", str(fixture_root.parent))
        return payload

    def assert_artifacts(self, work_dir: Path, scenario_id: str) -> None:
        prompt_target = read_utf8_json(work_dir / ".lgwf" / "prompt_convert_target.json")
        self.assertCountEqual(
            prompt_target.keys(),
            ["target_dir", "entry_files", "target_workflow_name", "target_package_root", "constraints"],
        )

        inspection = read_utf8_json(work_dir / ".lgwf" / "prompt_workflow_inspection.json")
        self.assertIn("source_summary", inspection)
        self.assertIn("detected_stages", inspection)
        self.assertIn("prompt_contracts", inspection)

        inspection_observe = read_utf8_json(work_dir / ".lgwf" / "prompt_workflow_inspection_observe.json")
        self.assertEqual(inspection_observe["verdict"], "pass")

        proposal = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_input_proposal.json")
        self.assertIn("workflow_name", proposal)
        self.assertIn("target_package_root", proposal)
        self.assertIn("raw_intent", proposal)

        proposal_observe = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_input_observe.json")
        self.assertEqual(proposal_observe["verdict"], "pass")

        approval = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_input_approval.json")
        self.assertEqual(approval.get("approval", approval.get("decision")), "approve")
        approval_value = approval.get("value")
        confirmed = approval_value.get("confirmed", {}) if isinstance(approval_value, dict) else {}
        confirmed_input = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_input.json")
        if not confirmed:
            confirmed = confirmed_input
        if scenario_id == "revise_then_approve":
            self.assertIn("handoff 给主 agent 启动 wf-create-fast", confirmed["raw_intent"])
            notes_text = json.dumps(confirmed["run_workflow_notes_for_wf_create_fast"], ensure_ascii=False)
            self.assertIn("主 agent 启动 wf-create-fast", notes_text)

        handoff_target = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_handoff.json")
        self.assertEqual(handoff_target["input_mode"], "converted_contract")
        self.assertFalse(str(handoff_target["target_package_root"]).startswith("/"))
        self.assertEqual(handoff_target["raw_intent"], confirmed.get("raw_intent", proposal["raw_intent"]))
        self.assertNotIn("source_root", handoff_target)
        self.assertNotIn("request", handoff_target)
        self.assertFalse((work_dir / ".lgwf" / "wf_create_fast_payload.json").exists())
        self.assertFalse((work_dir / ".lgwf" / "wf_create_fast_input_for_wf_create_fast.json").exists())
        launch_input = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_launch_input.json")
        self.assertEqual(launch_input["request"]["target_file"], str((work_dir / ".lgwf" / "wf_create_fast_handoff.json").resolve()))
        pending_files = sorted((work_dir / ".lgwf" / "handoff").glob("*.pending.json"))
        self.assertTrue(pending_files, "缺少 handoff pending 文件")
        pending = read_utf8_json(pending_files[-1])
        pending_text = json.dumps(pending, ensure_ascii=False)
        self.assertIn("wf_create_fast_launch_input", pending_text)
        self.assertEqual(pending["input_json_file"], str((work_dir / ".lgwf" / "wf_create_fast_launch_input.json").resolve()))
        self.assertIn("target_file", pending_text)
        self.assertIn("wf_create_fast_handoff.json", pending_text.replace("\\", "/"))
        run_workflow_trace = work_dir / RUNTIME_TRACE_DIRNAME / "run_workflow_trace.jsonl"
        self.assertFalse(run_workflow_trace.exists(), "wf-convert 不应直接启动 wf-create-fast")

    def assert_prompt_call_counts(self, call_log: list[dict[str, Any]], expected: dict[str, int]) -> None:
        counts: dict[str, int] = {}
        for item in call_log:
            self.assertTrue(item["matched"], f"fake Codex 命中 fallback: {item}")
            counts[item["prompt_key"]] = counts.get(item["prompt_key"], 0) + 1
        for prompt_key, expected_count in expected.items():
            self.assertEqual(counts.get(prompt_key, 0), expected_count, f"{prompt_key} 调用次数不匹配")

    def assert_approval_sequence(
        self,
        approval_events: list[dict[str, Any]],
        expected_nodes: list[str],
        *,
        scenario_id: str,
    ) -> None:
        actual_nodes = [item["node_id"] for item in approval_events]
        self.assertEqual(actual_nodes, expected_nodes, f"{scenario_id} approval 序列不匹配: {approval_events}")

    def assert_start_command_contract(self, work_dir: Path) -> None:
        command_log = work_dir / RUNTIME_TRACE_DIRNAME / "command_trace.jsonl"
        commands = []
        for line in command_log.read_text(encoding="utf-8").splitlines():
            payload = json.loads(line)
            if "command" in payload:
                commands.append(payload["command"])
        run_commands = [command for command in commands if len(command) >= 3 and command[2] == "run"]
        self.assertTrue(run_commands, f"未记录 run 命令: {commands}")
        self.assertNotIn("--rerun-existing", run_commands[0], f"首个 run 命令不应无条件带 rerun: {run_commands[0]}")

    def test_happy_path(self) -> None:
        scenario = {
            "scenario_id": "happy_path",
            "approval_steps": [
                {
                    "approval_node": "collect_prompt_workflow_target",
                    "submit_value": {
                        "target_dir": "<temp_fixture_root>/sample_prompt_workflow",
                        "entry_files": ["README.md", "flow/workflow.lgwf"],
                        "target_workflow_name": "demo-converted-workflow",
                        "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                        "constraints": ["不直接生成最终 LGWF workflow", "不自动调用 wf-create-fast"],
                    },
                },
                {
                    "approval_node": "confirm_create_input",
                    "submit_value": {
                        "approval": "approve",
                        "comment": "原样确认 proposal",
                        "confirmed": {
                            "workflow_name": "demo-converted-workflow",
                            "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                            "raw_intent": "把现有 prompt workflow 转成 LGWF workflow，并输出可交给 wf-create-fast 的完整 handoff target。",
                            "source_root": "<temp_fixture_root>/sample_prompt_workflow",
                            "stages": [
                                {"id": "discover", "summary": "索引源 prompt workflow 的入口、说明和 agent prompt"}
                            ],
                            "prompt_contracts": [
                                {"file": "flow/agents/inspect.md", "purpose": "分析源流程职责与输入输出约束"}
                            ],
                            "human_approval_points": ["confirm_create_input"],
                            "assumptions": ["源目录文本文件均可按 UTF-8 读取"],
                            "out_of_scope": ["不直接生成最终 workflow package"],
                            "run_workflow_notes_for_wf_create_fast": ["用户确认后 handoff 给主 agent 启动 wf-create-fast"],
                        },
                    },
                },
            ],
        }
        work_dir, phase_history, call_log, approval_events = self.run_scenario(scenario)
        self.assertTrue(
            any(item["phase"] == "waiting_review" for item in phase_history),
            f"happy_path 未进入 waiting_review: {phase_history}",
        )
        self.assertEqual(phase_history[-1]["phase"], "waiting_handoff")
        waiting_nodes = [
            item["current_node"]
            for item in phase_history
            if item["phase"] in {"waiting_human", "waiting_review"}
        ]
        self.assertIn("collect_prompt_workflow_target", waiting_nodes, phase_history)
        self.assertIn("confirm_create_input", waiting_nodes, phase_history)
        self.assert_approval_sequence(
            approval_events,
            ["collect_prompt_workflow_target", "confirm_create_input"],
            scenario_id=scenario["scenario_id"],
        )
        self.assert_start_command_contract(work_dir)
        self.assert_artifacts(work_dir, scenario["scenario_id"])
        self.assert_prompt_call_counts(
            call_log,
            {
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/reason.md": 1,
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/act.md": 1,
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/observe.md": 1,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/reason.md": 1,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": 1,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": 1,
            },
        )

    def test_revise_then_approve(self) -> None:
        scenario = {
            "scenario_id": "revise_then_approve",
            "approval_steps": [
                {
                    "approval_node": "collect_prompt_workflow_target",
                    "submit_value": {
                        "target_dir": "<temp_fixture_root>/sample_prompt_workflow",
                        "entry_files": ["README.md", "flow/workflow.lgwf"],
                        "target_workflow_name": "demo-converted-workflow",
                        "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                        "constraints": ["不直接生成最终 LGWF workflow", "不自动调用 wf-create-fast"],
                    },
                },
                {
                    "approval_node": "confirm_create_input",
                    "submit_value": {
                        "approval": "revise",
                        "comment": "先修订 proposal，再继续",
                        "changes": [
                            "raw_intent 需要明确“只产出 wf-create-fast handoff target，并 handoff 给主 agent 启动 wf-create-fast”",
                            "run_workflow_notes_for_wf_create_fast 需要补充用户确认后再接续的说明",
                        ],
                    },
                },
                {
                    "approval_node": "confirm_create_input",
                    "submit_value": {
                        "approval": "approve",
                        "comment": "按 revise 要求修订后通过",
                        "confirmed": {
                            "workflow_name": "demo-converted-workflow",
                            "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                            "raw_intent": "把现有 prompt workflow 转成可交给 wf-create-fast 的完整 handoff target；本 workflow 负责分析、proposal、人工确认，并在确认后 handoff 给主 agent 启动 wf-create-fast。",
                            "source_root": "<temp_fixture_root>/sample_prompt_workflow",
                            "stages": [
                                {"id": "discover", "summary": "索引入口与 prompt 资源"},
                                {"id": "analyze", "summary": "分析业务结构并整理给 wf-create-fast 的 handoff target"},
                            ],
                            "prompt_contracts": [
                                {"file": "flow/agents/inspect.md", "purpose": "分析源流程职责与输入输出约束"}
                            ],
                            "human_approval_points": ["confirm_create_input"],
                            "assumptions": ["样例源目录只覆盖文本文件索引与转换输入整理，不覆盖真实业务 happy path"],
                            "out_of_scope": ["不直接生成最终 workflow package"],
                            "run_workflow_notes_for_wf_create_fast": [
                                "requires_main_agent_confirmation=true",
                                "用户确认后由主 agent 启动 wf-create-fast",
                            ],
                        },
                    },
                },
            ],
        }
        work_dir, phase_history, call_log, approval_events = self.run_scenario(scenario)
        self.assertEqual(phase_history[-1]["phase"], "waiting_handoff")
        waiting_nodes = [
            item["current_node"]
            for item in phase_history
            if item["phase"] in {"waiting_human", "waiting_review"}
        ]
        self.assertIn("collect_prompt_workflow_target", waiting_nodes, phase_history)
        self.assertGreaterEqual(waiting_nodes.count("confirm_create_input"), 2, phase_history)
        self.assert_approval_sequence(
            approval_events,
            ["collect_prompt_workflow_target", "confirm_create_input", "confirm_create_input"],
            scenario_id=scenario["scenario_id"],
        )
        self.assertEqual(
            [item["decision"] for item in approval_events],
            ["approve", "revise", "approve"],
            f"{scenario['scenario_id']} approval submit 决策序列异常: {approval_events}",
        )
        self.assert_start_command_contract(work_dir)
        self.assert_artifacts(work_dir, scenario["scenario_id"])
        self.assert_prompt_call_counts(
            call_log,
            {
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/reason.md": 1,
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/act.md": 1,
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/observe.md": 1,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/reason.md": 2,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": 2,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": 2,
            },
        )
        propose_call_indexes = [
            item["call_index"]
            for item in call_log
            if item["prompt_key"] == "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md"
        ]
        self.assertEqual(propose_call_indexes, [1, 2])

    def test_observe_revise_then_pass(self) -> None:
        scenario = {
            "scenario_id": "observe_revise_then_pass",
            "approval_steps": [
                {
                    "approval_node": "collect_prompt_workflow_target",
                    "submit_value": {
                        "target_dir": "<temp_fixture_root>/sample_prompt_workflow",
                        "entry_files": ["README.md", "flow/workflow.lgwf"],
                        "target_workflow_name": "demo-converted-workflow",
                        "target_package_root": "skills/lgwf-wf-tools/workflows/generated/demo-converted-workflow",
                        "constraints": ["不直接生成最终 LGWF workflow", "不自动调用 wf-create-fast"],
                    },
                },
                {
                    "approval_node": "confirm_create_input",
                    "submit_value": {
                        "approval": "approve",
                        "comment": "observe revise 后第二轮已修复",
                    },
                },
            ],
        }
        work_dir, phase_history, call_log, approval_events = self.run_scenario(scenario)
        self.assertEqual(phase_history[-1]["phase"], "waiting_handoff")
        self.assert_approval_sequence(
            approval_events,
            ["collect_prompt_workflow_target", "confirm_create_input"],
            scenario_id=scenario["scenario_id"],
        )
        self.assert_start_command_contract(work_dir)
        self.assert_artifacts(work_dir, scenario["scenario_id"])
        self.assert_prompt_call_counts(
            call_log,
            {
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/reason.md": 1,
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/act.md": 1,
                "wf/04_confirm_business_flow/inspect_prompt_workflow_react/agents/observe.md": 1,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/reason.md": 2,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/act.md": 2,
                "wf/04_confirm_business_flow/propose_create_input_react/agents/observe.md": 2,
            },
        )
        proposal = read_utf8_json(work_dir / ".lgwf" / "wf_create_fast_input_proposal.json")
        self.assertEqual(proposal["stages"][0]["evidence_strength"], "high")


if __name__ == "__main__":
    unittest.main()
