"""校验打包产物基础结构。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact


def _load_confirmed_plan(root: Path) -> dict[str, Any]:
    confirmed_artifact = load_lgwf_artifact(root, "confirmed_packaging_plan.json")
    plan = confirmed_artifact.get("confirmed")
    if not isinstance(plan, dict):
        raise ValueError("confirmed_packaging_plan.json 缺少 confirmed 对象")
    return plan


def main() -> None:
    root = Path.cwd()
    plan = _load_confirmed_plan(root)
    materialized = load_lgwf_artifact(root, "materialized_package.json")
    output_skill_abs = Path(str(materialized["output_skill_abs"]))
    source_skill_abs = Path(str(materialized["source_skill_abs"]))

    required_paths = [
        "wf/workflow.lgwf",
        "vendor/lgwf-client-assist/scripts/lgwf.py",
        "scripts/run_local_lgwf_workflow.py",
        "PACKAGING_MANIFEST.json",
        "ws",
    ]
    issues: list[str] = []
    missing = [rel for rel in required_paths if not (output_skill_abs / rel).exists()]
    if missing:
        issues.extend([f"缺少关键产物：{rel}" for rel in missing])

    if (output_skill_abs / ".lgwf").exists():
        issues.append("打包产物根目录不应包含 .lgwf 运行态目录")
    if (output_skill_abs / "workflow.lgwf").exists():
        issues.append("打包产物根目录不应包含 workflow.lgwf，只允许 wf/workflow.lgwf")

    grandchild_workflows = []
    wf_root = output_skill_abs / "wf"
    if wf_root.is_dir():
        for workflow_path in wf_root.rglob("workflow.lgwf"):
            rel = workflow_path.relative_to(output_skill_abs).as_posix()
            if rel == "wf/workflow.lgwf":
                continue
            if len(Path(rel).parts) > 3:
                grandchild_workflows.append(rel)
    if grandchild_workflows:
        issues.extend([f"存在孙级 workflow：{rel}" for rel in grandchild_workflows])

    expected_source_docs = []
    source_docs_root = source_skill_abs / "wf" / "docs" / "steps"
    if source_docs_root.is_dir():
        expected_source_docs = [
            path.relative_to(source_skill_abs).as_posix()
            for path in sorted(source_docs_root.rglob("*.md"))
        ]
        for rel in expected_source_docs:
            if not (output_skill_abs / rel).is_file():
                issues.append(f"缺少源 skill 步骤文档副本：{rel}")

    context = {
        "workflow_name": "skill-packaging",
        "output_skill_abs": str(output_skill_abs),
        "source_skill_abs": str(source_skill_abs),
        "audit_smoke": bool(materialized.get("audit_smoke", True)),
        "required_manifest_keys": list(plan.get("manifest_plan", {}).get("required_keys", [])),
        "expected_source_docs": expected_source_docs,
        "checks": {
            "structure": {
                "required_paths": required_paths,
                "missing": missing,
                "grandchild_workflows": grandchild_workflows,
                "root_has_runtime_state": (output_skill_abs / ".lgwf").exists(),
                "root_has_workflow_lgwf": (output_skill_abs / "workflow.lgwf").exists(),
            }
        },
        "issues": issues,
    }
    print(
        json.dumps(
            {"skill_packaging.package_validation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

