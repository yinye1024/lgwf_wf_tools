from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = SELF_IMPROVE_ROOT.parent
DEFAULT_INCIDENT_DIR = FACADE_ROOT / ".local" / "self-improve" / "incidents"


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "incident"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_evidence(raw: str) -> Any:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("--evidence-json must be a JSON array")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["routing", "monitoring", "approval", "input_contract", "reporting", "release", "docs"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--severity", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--evidence-json", default="[]")
    parser.add_argument("--expected-behavior", default="")
    parser.add_argument("--actual-behavior", default="")
    parser.add_argument("--suspected-area", default="")
    parser.add_argument("--follow-up", default="add_eval", choices=["none", "add_eval", "create_proposal"])
    parser.add_argument("--output-dir", default=str(DEFAULT_INCIDENT_DIR))
    args = parser.parse_args()

    now = utc_now()
    incident_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{slugify(args.summary)}"
    incident = {
        "id": incident_id,
        "created_at": now.isoformat(),
        "type": args.type,
        "severity": args.severity,
        "summary": args.summary,
        "evidence": read_evidence(args.evidence_json),
        "expected_behavior": args.expected_behavior,
        "actual_behavior": args.actual_behavior,
        "suspected_area": args.suspected_area,
        "follow_up": args.follow_up,
    }
    output = Path(args.output_dir) / f"{incident_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(incident, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"incident": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
