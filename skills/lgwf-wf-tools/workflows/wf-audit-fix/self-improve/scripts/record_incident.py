from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any

from _paths import LOCAL_SELF_IMPROVE


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "incident"


def read_evidence(raw: str) -> Any:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("--evidence-json must be a JSON array")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["routing", "monitoring", "approval", "input_contract", "reporting", "release", "docs", "runtime", "quality"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--severity", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--evidence-json", default="[]")
    parser.add_argument("--expected-behavior", default="")
    parser.add_argument("--actual-behavior", default="")
    parser.add_argument("--suspected-area", default="")
    parser.add_argument("--follow-up", default="create_proposal", choices=["none", "add_eval", "create_proposal"])
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
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
    output = LOCAL_SELF_IMPROVE / "incidents" / f"{incident_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(incident, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"incident": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
