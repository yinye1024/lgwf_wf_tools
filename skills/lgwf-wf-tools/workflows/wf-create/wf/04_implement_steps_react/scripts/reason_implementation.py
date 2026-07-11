"""根据 observe 结果生成确定性的 implementation reason 文档。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def confirmed_payload(data: dict[str, Any]) -> dict[str, Any]:
    confirmed = data.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else data


def stage_names(step_designs: dict[str, Any]) -> list[str]:
    confirmed = confirmed_payload(step_designs)
    items = confirmed.get("source_business_flow_stages") or confirmed.get("step_designs") or []
    result: list[str] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            stage = str(item.get("stage_id") or item.get("stage") or "").strip()
            if stage and stage not in result:
                result.append(stage)
    return result


def failures_from_observe(observe: dict[str, Any]) -> list[str]:
    failures = observe.get("failures", [])
    if isinstance(failures, list):
        return [str(item).strip() for item in failures if str(item).strip()]
    if isinstance(failures, str) and failures.strip():
        return [failures.strip()]
    return ["首轮尚未执行 authoring audit"]


def build_reason(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    context = load_json(lgwf_dir / "implementation_context.json")
    step_designs = load_json(lgwf_dir / "step_designs.json")
    observe = load_json(lgwf_dir / "implementation_observe.json")
    failures = failures_from_observe(observe)
    target_package_abs = str(context.get("target_package_abs", "")).strip()
    target_package_root = str(context.get("target_package_root", "")).strip()
    stages = stage_names(step_designs)
    repair_files = ["wf/artifact_contracts.json"] if any("artifact_contracts.json" in item for item in failures) else []
    if not repair_files:
        repair_files = [
            "wf/workflow.lgwf",
            *[f"wf/{stage}/workflow.lgwf" for stage in stages],
        ]
    lines = [
        "# implement_steps_react reason",
        "",
        "## 本轮目标",
        "",
        "本轮 reason 由确定性脚本生成。目标是把上一轮 observe 的 authoring audit 失败转成最小 repair ACT 输入。",
        "",
        "## 目标包",
        "",
        f"- `target_package_root`：`{target_package_root}`",
        f"- `target_package_abs`：`{target_package_abs}`",
        "",
        "## audit 失败",
        "",
        *[f"- {item}" for item in failures],
        "",
        "## 本轮 ACT 必改文件",
        "",
        *[f"- `{path}`" for path in repair_files],
        "",
        "## 禁止修改范围",
        "",
        "- 不修改 LGWF runtime 或 `vendor/`。",
        "- 不手工修改 `.lgwf` runtime 状态；由 workflow 脚本写入必要产物。",
        "- 不扩展到 registry 注册、发布或端到端业务保证。",
        "",
        "## 完成后 observe 检查",
        "",
        "- 重新执行目标 `wf/workflow.lgwf` authoring audit。",
        "- 如果 audit 通过，`decide` 应退出 ReAct；否则只按新的 diagnostics 进入下一轮 repair。",
    ]
    output_path = lgwf_dir / "implementation_reason.md"
    write_text(output_path, "\n".join(lines))
    return {
        "status": "ok",
        "reason_path": ".lgwf/implementation_reason.md",
        "target_package_root": target_package_root,
        "repair_files": repair_files,
        "failure_count": len(failures),
    }


def main() -> None:
    result = build_reason(Path.cwd())
    print(json.dumps({"lgwf_wf_create.implementation_reason_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
