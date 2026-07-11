"""确定性补齐目标 package 的 Contract 文档并记录结果。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = ("模块定位", "入口", "依赖", "状态边界", "产物", "验证", "禁止事项")
CONTRACT_DOCS = ("AGENTS.md", "README.md")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_workspace_root(work_dir: Path, implementation_context: dict[str, Any]) -> Path:
    raw = str(implementation_context.get("workspace_root", "")).strip()
    if raw:
        candidate = Path(raw).resolve()
        if candidate.exists():
            return candidate
    current = work_dir.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "skills").is_dir():
            return candidate
    raise RuntimeError(f"无法从运行目录推导 workspace_root: {work_dir}")


def resolve_target_package(work_dir: Path, implementation_context: dict[str, Any]) -> Path:
    target_package_abs = str(implementation_context.get("target_package_abs", "")).strip()
    if target_package_abs:
        return Path(target_package_abs).resolve()
    workspace_root = find_workspace_root(work_dir, implementation_context)
    target_package_root = str(implementation_context.get("target_package_root", "")).strip()
    if target_package_root:
        return (workspace_root / target_package_root).resolve()
    return workspace_root


def missing_contract_sections(target_abs: Path) -> list[str]:
    combined = "\n".join(read_text(target_abs / name) for name in CONTRACT_DOCS)
    return [section for section in REQUIRED_SECTIONS if section not in combined]


def append_missing_sections(target_abs: Path, missing: list[str]) -> list[str]:
    if not missing:
        return []
    doc_path = target_abs / "AGENTS.md"
    existing = read_text(doc_path).rstrip()
    if not existing:
        existing = f"# {target_abs.name} 协作指引\n"

    section_templates = {
        "模块定位": "本模块是由 wf-create 生成或补齐的自包含工作流 package，用于完成已确认的目标任务。",
        "入口": "主要入口以本模块 README、SKILL.md 或 wf/workflow.lgwf 的实际存在情况为准。",
        "依赖": "依赖 Python 标准库和仓库内已声明的 LGWF 工具链；不得隐式依赖本地未记录环境。",
        "状态边界": "运行状态应写入工作目录下的 .lgwf，不得污染目标 package 根目录或无关源码。",
        "产物": "产物以 wf/artifact_contracts.json、workflow CONTRACT 和 README 中声明的路径为准。",
        "验证": "至少运行目标 workflow 的 lgwf.py audit，并按模块 README 中的测试命令执行最小验证。",
        "禁止事项": "不得绕过人工确认边界，不得修改无关文件，不得自动发布或注册 registry。",
    }
    additions = []
    for section in missing:
        additions.append(f"## {section}\n\n{section_templates[section]}\n")
    write_text(doc_path, existing + "\n\n" + "\n".join(additions))
    return ["AGENTS.md"]


def list_workflow_files(target_abs: Path) -> list[str]:
    workflow_files = sorted(target_abs.glob("wf/**/workflow.lgwf"))
    return [path.relative_to(target_abs).as_posix() for path in workflow_files]


def build_node_contract_summary(target_abs: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for workflow_path in sorted(target_abs.glob("wf/**/workflow.lgwf")):
        text = read_text(workflow_path)
        if not text:
            continue
        relative = workflow_path.relative_to(target_abs).as_posix()
        summaries.append(
            {
                "workflow": relative,
                "has_contract_blocks": "CONTRACT {" in text,
                "output_markers": {
                    "OUTPUT_JSON": "OUTPUT_JSON" in text,
                    "OUTPUT_FILE": "OUTPUT_FILE" in text,
                    "PERSIST": "PERSIST" in text,
                },
            }
        )
    return summaries


def apply_contract_enrichment(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    target_abs = resolve_target_package(work_dir, implementation_context)
    target_package_root = str(implementation_context.get("target_package_root", "")).strip()

    if not target_abs.is_dir():
        result = {
            "target_package_root": target_package_root,
            "target_package_abs": str(target_abs),
            "contract_files": [],
            "workflow_files": [],
            "node_contracts_updated": [],
            "updated_sections": [],
            "validation_notes": [],
            "remaining_risks": [f"目标 package 不存在: {target_abs}"],
        }
        write_json(lgwf_dir / "contract_enrichment_result.json", result)
        return result

    missing_before = missing_contract_sections(target_abs)
    touched_docs = append_missing_sections(target_abs, missing_before)
    missing_after = missing_contract_sections(target_abs)
    workflow_files = list_workflow_files(target_abs)
    contract_summary = build_node_contract_summary(target_abs)

    result = {
        "target_package_root": target_package_root,
        "target_package_abs": str(target_abs),
        "contract_files": [name for name in CONTRACT_DOCS if (target_abs / name).is_file()],
        "workflow_files": workflow_files,
        "node_contracts_updated": [],
        "contract_summary": contract_summary,
        "updated_sections": missing_before,
        "validation_notes": [
            "入口文档 Contract 段落已检查，缺失段落已补到 AGENTS.md。" if touched_docs else "入口文档 Contract 段落已覆盖。",
            "节点级 Contract 保持实现阶段生成结果，由 observe 阶段的 lgwf.py audit 验收。",
        ],
        "remaining_risks": [f"仍缺少 Contract 段落: {', '.join(missing_after)}"] if missing_after else [],
    }
    write_json(lgwf_dir / "contract_enrichment_result.json", result)
    return result


def main() -> None:
    result = apply_contract_enrichment(Path.cwd())
    print(json.dumps({"lgwf_wf_create.contract_enrichment": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
