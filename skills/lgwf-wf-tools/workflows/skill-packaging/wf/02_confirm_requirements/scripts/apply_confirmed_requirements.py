from __future__ import annotations

import json
import sys


def main() -> None:
    proposal = json.loads(sys.stdin.read() or "{}")
    confirmed = {
        "workflow_name": proposal.get("workflow_name", "LGWF Skill Packaging Workflow"),
        "source_skill": proposal.get("source_skill", "<source-skill>"),
        "output_parent": proposal.get("output_parent", "<output-parent>"),
        "force": proposal.get("force", False),
        "status_boundary": "ws/.lgwf",
    }
    json.dump(confirmed, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
