from __future__ import annotations

import json
import sys


def build_scaffold_plan(requirements: dict) -> dict:
    return {
        "workflow_name": requirements.get("workflow_name", "LGWF Skill Packaging Workflow"),
        "target_package_root": "skills/lgwf-wf-tools/workflows/skill-packaging",
        "package_profile": "internal_workflow_package",
        "template": {
            "template_id": "workflow_packaged_skill",
            "template_version": 1,
        },
        "rules": {
            "path_policy": [
                "只使用相对路径",
                "根目录不生成 workflow.lgwf",
                "不生成根 SKILL.md",
            ],
            "state_boundary": [
                "运行状态只写入 ws/.lgwf",
                "不向目标 package 根目录写入 `.lgwf`",
            ],
        },
        "create_dirs": [
            "scripts",
            "tests",
            "ws",
            "wf",
            "wf/shared/scripts",
            "wf/docs/steps",
            "wf/02_confirm_requirements",
            "wf/04_confirm_business_flow",
            "wf/07_confirm_step_designs",
            "wf/09_summarize_create_result",
        ],
        "create_files": [
            "AGENTS.md",
            "README.md",
            "wf/workflow.lgwf",
            "wf/02_confirm_requirements/workflow.lgwf",
            "wf/04_confirm_business_flow/workflow.lgwf",
            "wf/07_confirm_step_designs/workflow.lgwf",
            "wf/09_summarize_create_result/workflow.lgwf",
            "tests/test_scaffold_package_rules.py",
        ],
        "placeholders": {
            "ws": "运行状态写入 ws/.lgwf",
            "wf": "唯一 workflow package root",
            "tests/test_scaffold_package_rules.py": "最小脚手架边界验证",
        },
        "derived_from_business_flow": [
            "request_intake",
            "preflight_validation",
            "plan_confirmation",
            "package_execution",
            "package_verification",
            "result_summary",
        ],
    }


def main() -> None:
    requirements = json.loads(sys.stdin.read() or "{}")
    json.dump(build_scaffold_plan(requirements), sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
