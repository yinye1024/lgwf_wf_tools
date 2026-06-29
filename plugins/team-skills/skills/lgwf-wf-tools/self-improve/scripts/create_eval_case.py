from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = SELF_IMPROVE_ROOT.parent
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "eval-case-drafts"


CATEGORY_TO_WORKFLOW = {
    "routing": "wf-fix",
    "monitoring": "",
    "approval": "",
    "input_contract": "",
    "reporting": "",
    "release": "",
    "docs": "",
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "eval-case"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def case_from_incident(incident: dict[str, Any]) -> dict[str, Any]:
    category = str(incident.get("type") or "routing")
    summary = str(incident.get("summary") or "self improve incident")
    expected: dict[str, Any] = {
        "must_read": ["AGENTS.md", "registry.json"],
        "required_text": [
            {
                "path": "AGENTS.md",
                "contains": "Self Improve 触发与产出",
            }
        ],
    }
    workflow_id = CATEGORY_TO_WORKFLOW.get(category, "")
    if workflow_id:
        expected["workflow_id"] = workflow_id
    return {
        "id": f"draft-{slugify(summary)}",
        "category": category if category in {"routing", "monitoring", "approval", "input_contract", "release", "reporting"} else "reporting",
        "input": {
            "user_request": summary,
            "context": incident.get("evidence", []),
            "source_incident": incident.get("id", ""),
        },
        "expected": expected,
        "review_status": "draft",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    incident_path = Path(args.incident)
    incident = read_json(incident_path)
    case = case_from_incident(incident)
    envelope = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_incident": str(incident_path),
        "cases": [case],
    }
    output = Path(args.output_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{case['id']}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"eval_case": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
