"""汇总 `lgwf-wf-create` 第一版的创建结果。

当前阶段只定义未来运行时的结果汇总接口，不承诺已经完成
`lgwf-wf-prompt-fix` 自动调用、生成出的目标 workflow 自动接入 facade 路由、
自动修复或端到端业务成功。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


DEFAULT_SCOPE_BOUNDARY = {
    "in_scope": [
        "workflow package 初稿结构",
        "需求方案 proposal/approval 接口",
        "业务流转 proposal/approval 接口",
        "脚手架规则与路径边界",
        "步骤设计模板、确认模板与实现初稿接口",
        "结果汇总接口与最小结构性验证入口",
    ],
    "out_of_scope": [
        "lgwf-wf-prompt-fix 集成",
        "生成出的目标 workflow 自动接入 facade 路由",
        "自动修复或自动重试",
        "端到端业务 happy path 保证",
        "自动接入后续治理 workflow",
    ],
}

DEFAULT_RUNTIME_ARTIFACTS = [
    ".lgwf/raw_intent_request.json",
    ".lgwf/create_requirements_proposal.json",
    ".lgwf/create_requirements_approval.json",
    ".lgwf/create_requirements.json",
    ".lgwf/business_flow_proposal.json",
    ".lgwf/business_flow_approval.json",
    ".lgwf/business_flow.json",
    ".lgwf/step_designs_proposal.json",
    ".lgwf/step_design_confirmation_record.json",
    ".lgwf/implementation_audit_result.json",
    ".lgwf/implementation_observe.json",
    ".lgwf/implementation_decision.json",
    ".lgwf/step_designs.json",
    ".lgwf/implementation_result.json",
    ".lgwf/create_result_summary.json",
]


def normalize_relative_path(raw_path: str, field_name: str) -> str:
    """只允许报告包内相对路径，避免汇总产物误收运行状态或外部路径。"""

    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute():
        raise ValueError(f"{field_name} 只使用相对路径，禁止绝对路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止指向 `.lgwf` 运行状态目录")
    if ":" in cleaned:
        raise ValueError(f"{field_name} 禁止盘符路径")
    normalized = candidate.as_posix().strip("/")
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def normalize_runtime_artifact_path(raw_path: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned:
        raise ValueError("runtime_artifacts 不能为空")
    if candidate.is_absolute() or ":" in cleaned:
        raise ValueError("runtime_artifacts 禁止绝对路径和盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError("runtime_artifacts 禁止 `..`")
    normalized = candidate.as_posix().strip("/")
    if not normalized.startswith(".lgwf/") and not normalized.startswith("reports/"):
        raise ValueError("runtime_artifacts 只允许 `.lgwf/` 或 `reports/` 下的运行期产物")
    return normalized


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def strip_package_root(path: str, package_root: str) -> str:
    normalized_path = path.replace("\\", "/").strip("/")
    normalized_root = package_root.replace("\\", "/").strip("/")
    if normalized_path == normalized_root:
        return "."
    prefix = f"{normalized_root}/"
    if normalized_path.startswith(prefix):
        return normalized_path[len(prefix) :]
    return normalized_path


def payload_from_implementation_result(root: Path) -> dict[str, Any]:
    implementation = load_json(root / ".lgwf" / "implementation_result.json")
    if not implementation:
        return {}
    audit_result = load_json(root / ".lgwf" / "implementation_audit_result.json")
    observe_result = load_json(root / ".lgwf" / "implementation_observe.json")
    package_root = str(implementation.get("target_package_root", "")).strip()
    workflow_name = str(implementation.get("workflow_name", "")).strip()
    if not package_root or not workflow_name:
        return {}
    generated = implementation.get("generated", {})
    produced_files: list[str] = []
    if isinstance(generated, dict):
        root_files = generated.get("root_files", [])
        if isinstance(root_files, list):
            produced_files.extend(str(path) for path in root_files if str(path).strip())
        by_step = generated.get("by_step", [])
        if isinstance(by_step, list):
            for item in by_step:
                if not isinstance(item, dict):
                    continue
                files = item.get("generated_files", [])
                if isinstance(files, list):
                    produced_files.extend(str(path) for path in files if str(path).strip())
    produced_files = [strip_package_root(path, package_root) for path in produced_files]
    verification = implementation.get("verification", [])
    validation_entry = ""
    if isinstance(verification, list):
        for item in verification:
            if isinstance(item, dict) and str(item.get("command", "")).strip():
                validation_entry = str(item["command"]).strip()
                break
    payload: dict[str, Any] = {
        "workflow_name": workflow_name,
        "target_package_root": package_root,
    }
    if produced_files:
        payload["produced_files"] = produced_files
    if validation_entry:
        payload["validation_entry"] = validation_entry
    if audit_result:
        payload["implementation_audit"] = {
            "passed": audit_result.get("passed"),
            "status": audit_result.get("status"),
            "needs_post_fix": bool(audit_result.get("needs_post_fix")),
            "failures": audit_result.get("failures", []),
        }
    elif observe_result:
        payload["implementation_audit"] = {
            "passed": observe_result.get("passed"),
            "status": observe_result.get("status"),
            "needs_post_fix": bool(observe_result.get("needs_post_fix")),
            "failures": observe_result.get("failures", []),
        }
    return payload


def payload_from_confirmed_artifacts(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    requirements = load_json(lgwf_dir / "create_requirements.json").get("confirmed", {})
    business_flow = load_json(lgwf_dir / "business_flow.json").get("confirmed", {})
    if not isinstance(requirements, dict):
        requirements = {}
    if not isinstance(business_flow, dict):
        business_flow = {}
    workflow_name = str(requirements.get("workflow_name") or business_flow.get("workflow_name") or "").strip()
    package_root = str(
        requirements.get("target_package_root") or business_flow.get("target_package_root") or ""
    ).strip()
    if not workflow_name or not package_root:
        return {}
    return {
        "workflow_name": workflow_name,
        "target_package_root": package_root,
    }


def read_stdin_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    except OSError:
        raw = ""
    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("stdin payload 必须是 JSON object")
    return data


def build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """构建可审查的创建结果汇总。"""

    package_root = normalize_relative_path(
        str(payload.get("target_package_root", "skills/lgwf-wf-tools/workflows/wf-create")),
        "target_package_root",
    )
    workflow_name = str(payload.get("workflow_name", "lgwf-wf-create")).strip()
    produced_files = payload.get(
        "produced_files",
        [
            "wf/workflow.lgwf",
            "README.md",
            "AGENTS.md",
            "tests/test_structured_contracts.py",
            "wf/06_summarize_create_result/scripts/summarize_create_result.py",
        ],
    )
    if not isinstance(produced_files, list):
        raise TypeError("produced_files 必须是路径字符串数组")
    produced_files = [normalize_relative_path(str(path), "produced_files") for path in produced_files]
    validation_entry = str(payload.get("validation_entry", "python -m unittest discover tests")).strip()
    runtime_artifacts = payload.get("runtime_artifacts", DEFAULT_RUNTIME_ARTIFACTS)
    if not isinstance(runtime_artifacts, list):
        raise TypeError("runtime_artifacts 必须是路径字符串数组")
    runtime_artifacts = [normalize_runtime_artifact_path(str(path)) for path in runtime_artifacts]

    implementation_audit = payload.get("implementation_audit", {})
    if not isinstance(implementation_audit, dict):
        implementation_audit = {}
    audit_status = str(implementation_audit.get("status") or "").strip()
    needs_post_fix = bool(implementation_audit.get("needs_post_fix"))
    status = "draft_structure_ready"
    if needs_post_fix:
        status = "draft_needs_post_fix"
    elif audit_status and audit_status != "passed":
        status = "draft_needs_implementation_repair"

    return {
        "workflow_name": workflow_name or "lgwf-wf-create",
        "target_package_root": package_root,
        "summary_version": 1,
        "result_kind": "workflow_package_draft_summary",
        "status": status,
        "produced_files": produced_files,
        "runtime_artifacts": runtime_artifacts,
        "implementation_audit": implementation_audit,
        "validation": {
            "minimal_command": validation_entry,
            "checks": [
                "implement_steps_react observe 确定性检测",
                "workflow 结构性 audit",
                "关键文件存在性",
                "resource path 相对路径规则",
                "work dir 边界仅允许 ws/.lgwf",
                "中文 UTF-8 文档可读性",
                "approval route 与 confirmed artifact 固化契约",
            ],
        },
        "scope_boundary": payload.get("scope_boundary", DEFAULT_SCOPE_BOUNDARY),
        "notes": [
            "本汇总接口只描述第一版 package 初稿的结构性完成情况。",
            "未来运行时可在此基础上补充真实执行产物统计，但当前不宣称后续 workflow 已集成。",
        ],
    }


def write_report(root: Path, summary: dict[str, Any]) -> Path:
    relative_path = Path("reports") / "create-workflow" / "create_result_report.md"
    report_dir = root / relative_path.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = root / relative_path
    lines = [
        f"# {summary['workflow_name']} 结果汇总",
        "",
        f"- workflow：`{summary['workflow_name']}`",
        f"- 状态：`{summary['status']}`",
        f"- 最小验证：`{summary['validation']['minimal_command']}`",
        f"- 实现验收：`{summary.get('implementation_audit', {}).get('status', 'unknown')}`",
        "",
        "## 产物",
        "",
        *[f"- `{path}`" for path in summary["produced_files"]],
        "",
        "## 运行期产物",
        "",
        *[f"- `{path}`" for path in summary["runtime_artifacts"]],
        "",
        "## 范围边界",
        "",
        *[f"- {item}" for item in summary["scope_boundary"]["out_of_scope"]],
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return relative_path


def main() -> None:
    payload = read_stdin_payload()
    if not payload:
        payload = payload_from_implementation_result(Path.cwd())
    if not payload:
        payload = payload_from_confirmed_artifacts(Path.cwd())
    summary = build_summary(payload)
    report_path = write_report(Path.cwd(), summary)
    summary["report_path"] = report_path.as_posix()
    summary_path = Path.cwd() / ".lgwf" / "create_result_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
