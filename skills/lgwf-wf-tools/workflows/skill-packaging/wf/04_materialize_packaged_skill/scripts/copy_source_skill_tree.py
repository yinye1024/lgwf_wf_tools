"""复制源 skill 到目标输出目录。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import copy_tree_filtered, load_lgwf_artifact, remove_existing_output


def _load_confirmed_plan(root: Path) -> dict[str, Any]:
    confirmed_artifact = load_lgwf_artifact(root, "confirmed_packaging_plan.json")
    plan = confirmed_artifact.get("confirmed")
    if not isinstance(plan, dict):
        raise ValueError("confirmed_packaging_plan.json 缺少 confirmed 对象")
    return plan


def _require_path(value: Any, field_name: str) -> Path:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} 不能为空")
    return Path(text)


def _ensure_within_root(output_parent_abs: Path, output_skill_abs: Path) -> None:
    try:
        output_skill_abs.resolve().relative_to(output_parent_abs.resolve())
    except ValueError as exc:
        raise ValueError("output_skill_abs 必须位于 output_parent_abs 之下") from exc


def main() -> None:
    root = Path.cwd()
    plan = _load_confirmed_plan(root)
    preflight = load_lgwf_artifact(root, "packaging_preflight.json")

    source_skill_abs = _require_path(plan.get("source_skill", {}).get("abs_path"), "source_skill.abs_path")
    output_parent_abs = _require_path(plan.get("output", {}).get("output_parent_abs"), "output.output_parent_abs")
    output_skill_abs = _require_path(plan.get("output", {}).get("output_skill_abs"), "output.output_skill_abs")
    runtime_source_abs = _require_path(plan.get("runtime", {}).get("runtime_source_abs"), "runtime.runtime_source_abs")

    if not source_skill_abs.is_dir():
        raise FileNotFoundError(f"源 skill 不存在：{source_skill_abs}")
    _ensure_within_root(output_parent_abs, output_skill_abs)

    target_existed = output_skill_abs.exists()
    if target_existed:
        remove_existing_output(output_skill_abs)
    output_parent_abs.mkdir(parents=True, exist_ok=True)
    copy_tree_filtered(source_skill_abs, output_skill_abs)
    (output_skill_abs / "ws").mkdir(parents=True, exist_ok=True)

    source_docs_root = source_skill_abs / "wf" / "docs" / "steps"
    source_step_docs = []
    if source_docs_root.is_dir():
        source_step_docs = [
            path.relative_to(source_skill_abs).as_posix()
            for path in sorted(source_docs_root.rglob("*.md"))
        ]

    context = {
        "workflow_name": "skill-packaging",
        "source_skill_abs": str(source_skill_abs),
        "output_parent_abs": str(output_parent_abs),
        "output_skill_abs": str(output_skill_abs),
        "runtime_source_abs": str(runtime_source_abs),
        "audit_smoke": bool(plan.get("audit_smoke", True)),
        "manifest_required_keys": plan.get("manifest_plan", {}).get("required_keys", []),
        "runner_relative_path": plan.get("runner_plan", {}).get("path", "scripts/run_local_lgwf_workflow.py"),
        "runtime_relative_path": "vendor/lgwf-client-assist",
        "target_existed_before_copy": target_existed,
        "preflight": preflight,
        "source_step_docs": source_step_docs,
        "generated_outputs": ["ws/"],
    }
    print(
        json.dumps(
            {"skill_packaging.materialization_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

