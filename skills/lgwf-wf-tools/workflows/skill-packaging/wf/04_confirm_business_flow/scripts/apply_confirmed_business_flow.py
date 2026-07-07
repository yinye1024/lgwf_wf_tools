from __future__ import annotations

import json
import sys


def main() -> None:
    plan = json.loads(sys.stdin.read() or "{}")
    confirmed = {
        "workflow_name": plan.get("workflow_name", "LGWF Skill Packaging Workflow"),
        "target_package_root": plan.get("target_package_root", "skills/lgwf-wf-tools/workflows/skill-packaging"),
        "package_profile": plan.get("package_profile", "internal_workflow_package"),
        "create_dirs": plan.get("create_dirs", []),
        "create_files": plan.get("create_files", []),
    }
    json.dump(confirmed, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
