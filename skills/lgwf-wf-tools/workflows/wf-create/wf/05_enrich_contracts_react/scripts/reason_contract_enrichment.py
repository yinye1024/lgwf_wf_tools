"""生成 Contract 补强阶段的确定性执行计划。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = ("模块定位", "入口", "依赖", "状态边界", "产物", "验证", "禁止事项")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_reason(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    implementation_result = read_json(lgwf_dir / "implementation_result.json")
    observe = read_json(lgwf_dir / "contract_observe.json")

    target_package_root = str(implementation_context.get("target_package_root", "")).strip()
    target_package_abs = str(implementation_context.get("target_package_abs", "")).strip()
    generated_files = implementation_result.get("generated_files")
    if not isinstance(generated_files, list):
        generated_files = []

    failures = observe.get("failures")
    if not isinstance(failures, list):
        failures = []

    plan = {
        "target_package_root": target_package_root,
        "target_package_abs": target_package_abs,
        "required_sections": list(REQUIRED_SECTIONS),
        "observed_failures": failures,
        "planned_actions": [
            "检查 AGENTS.md 与 README.md 是否合并覆盖模块 Contract 必备段落。",
            "缺少段落时只在目标 package 的 AGENTS.md 追加最小中文说明。",
            "枚举目标 package 内 workflow.lgwf，记录当前节点级 Contract 状态。",
            "写出 .lgwf/contract_enrichment_result.json，交由 observe 阶段运行 lgwf.py audit。",
        ],
        "generated_file_count": len(generated_files),
    }

    failure_lines = "\n".join(f"- {item}" for item in failures) if failures else "- 无"
    reason_md = f"""# Contract 补强计划

## 目标

- target_package_root: `{target_package_root}`
- target_package_abs: `{target_package_abs}`

## 上轮 observe 失败项

{failure_lines}

## 本轮动作

1. 检查入口文档是否覆盖：{", ".join(REQUIRED_SECTIONS)}。
2. 如有缺口，只在目标 package 内补齐入口文档，不改业务拓扑。
3. 枚举 `wf/workflow.lgwf` 与阶段 workflow，记录本轮 Contract 补强结果。
4. 写出 `.lgwf/contract_enrichment_result.json`，随后由 observe 阶段执行 `lgwf.py audit`。

## 不做事项

- 不修改 LGWF runtime 或 vendor。
- 不写 facade registry。
- 不改目标 workflow 的业务阶段、路由或审批语义。
"""
    write_text(lgwf_dir / "contract_reason.md", reason_md)
    return plan


def main() -> None:
    plan = build_reason(Path.cwd())
    print(json.dumps({"lgwf_wf_create.contract_reason": plan}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
