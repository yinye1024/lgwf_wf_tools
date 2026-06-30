from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = SELF_IMPROVE_ROOT / "evals"


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:64] or "promoted-eval-case"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def promoted_payload(draft: dict[str, Any], approved_by: str) -> dict[str, Any]:
    cases = draft.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("draft must contain non-empty cases list")
    promoted_cases = []
    for raw_case in cases:
        if not isinstance(raw_case, dict):
            raise ValueError("case must be object")
        case = dict(raw_case)
        if case.get("review_status") != "draft":
            raise ValueError("only draft eval cases can be promoted")
        case.pop("review_status", None)
        promoted_cases.append(case)
    return {
        "version": 1,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "approved_by": approved_by,
        "cases": promoted_cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    if not args.approved_by.strip():
        raise ValueError("--approved-by is required")
    draft_path = Path(args.draft)
    payload = promoted_payload(read_json(draft_path), args.approved_by.strip())
    first_case = payload["cases"][0]
    output = Path(args.output_dir) / f"promoted-{slugify(str(first_case.get('id', 'eval-case')))}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"promoted_eval": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
