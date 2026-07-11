"""生成结构化打包计划草案。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from packaging_common import load_lgwf_artifact, write_json


def main() -> None:
    root = Path.cwd()
    request = load_lgwf_artifact(root, "packaging_request.json")
    preflight = load_lgwf_artifact(root, "packaging_preflight.json")
    write_scope = load_lgwf_artifact(root, "packaging_write_scope.json")

    source_ok = bool(preflight.get("source_skill", {}).get("ok"))
    runtime_ok = bool(preflight.get("runtime", {}).get("ok"))
    output_info = preflight.get("output", {})
    target_exists = bool(output_info.get("target_exists"))

    proposal = {
        "proposal_kind": "packaging_plan_proposal",
        "workflow_name": "skill-packaging",
        "source_skill": {
            "path": request.get("source_skill"),
            "abs_path": request.get("source_skill_abs"),
            "name": Path(str(request["source_skill_abs"])).name,
        },
        "output": {
            "output_parent": request.get("output_parent"),
            "output_parent_abs": request.get("output_parent_abs"),
            "output_skill_abs": write_scope.get("output_skill_abs"),
            "force": bool(request.get("force", False)),
        },
        "runtime": {
            "runtime_source": request.get("runtime_source"),
            "runtime_source_abs": request.get("runtime_source_abs"),
        },
        "copy_plan": {
            "mode": "copytree_filtered",
            "excluded_names": [
                ".git",
                ".lgwf",
                ".local",
                ".mypy_cache",
                ".pytest_cache",
                "__pycache__",
                "reports",
                "ws",
            ],
            "excluded_suffixes": [".pyc", ".pyo"],
        },
        "runner_plan": {
            "path": "scripts/run_local_lgwf_workflow.py",
            "runtime_relative_path": "vendor/lgwf-client-assist/scripts/lgwf.py",
        },
        "manifest_plan": {
            "path": "PACKAGING_MANIFEST.json",
            "required_keys": [
                "packager",
                "source_skill_name",
                "runtime_relative_path",
                "local_runner",
            ],
        },
        "audit_smoke": bool(request.get("audit_smoke", True)),
        "ready_to_package": source_ok and runtime_ok,
        "risks": [
            *(
                ["输出目录已存在，执行前必须显式确认覆盖风险"]
                if target_exists
                else []
            ),
            "当前 facade registry 仍将 skill-packaging 声明为 tool-workflow；切换为 lgwf 需要单独确认。",
        ],
        "pending_decisions": [
            "是否保留 facade 根 scripts/package_lgwf_skill.py 兼容入口",
            "是否在后续治理中把 registry.kind 从 tool-workflow 切到 lgwf",
        ],
        "preflight": preflight,
    }
    write_json(root / ".lgwf" / "packaging_plan_proposal.json", proposal)
    print(
        json.dumps(
            {"skill_packaging.packaging_plan_proposal": proposal},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
