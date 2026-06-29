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


def build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """构建可审查的创建结果汇总。"""

    package_root = normalize_relative_path(
        str(payload.get("target_package_root", "plugins/team-skills/skills/lgwf-wf-tools/workflows/wf-create")),
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
            "wf/09_summarize_create_result/scripts/summarize_create_result.py",
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

    return {
        "workflow_name": workflow_name or "lgwf-wf-create",
        "target_package_root": package_root,
        "summary_version": 1,
        "result_kind": "workflow_package_draft_summary",
        "status": "draft_structure_ready",
        "produced_files": produced_files,
        "runtime_artifacts": runtime_artifacts,
        "validation": {
            "minimal_command": validation_entry,
            "checks": [
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
        "# lgwf-wf-create 结果汇总",
        "",
        f"- workflow：`{summary['workflow_name']}`",
        f"- 状态：`{summary['status']}`",
        f"- 最小验证：`{summary['validation']['minimal_command']}`",
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
    payload = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    summary = build_summary(payload)
    report_path = write_report(Path.cwd(), summary)
    summary["report_path"] = report_path.as_posix()
    summary_path = Path.cwd() / ".lgwf" / "create_result_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
