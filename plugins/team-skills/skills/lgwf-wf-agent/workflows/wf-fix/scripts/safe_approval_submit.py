from __future__ import annotations

import argparse
import base64
import copy
import json
import sys
from pathlib import Path
from typing import Any

from lgwf_client.main_agent.approvals import submit_main_agent_approval


def default_lgwf_facade() -> Path:
    lgwf_py = Path(__file__).resolve().parents[3] / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
    if not lgwf_py.is_file():
        raise FileNotFoundError(f"missing bundled lgwf-client-assist: {lgwf_py}")
    return lgwf_py


def load_json_value(args: argparse.Namespace) -> Any | None:
    provided = [
        args.value_file is not None,
        args.value_json_ascii is not None,
        args.value_json_base64 is not None,
    ]
    if sum(provided) > 1:
        raise ValueError("use only one of --value-file, --value-json-ascii, or --value-json-base64")
    if args.value_file is not None:
        return json.loads(Path(args.value_file).read_text(encoding="utf-8"))
    if args.value_json_ascii is not None:
        args.value_json_ascii.encode("ascii")
        return json.loads(args.value_json_ascii)
    if args.value_json_base64 is not None:
        raw = base64.b64decode(args.value_json_base64, validate=True)
        return json.loads(raw.decode("utf-8"))
    return None


def find_nested_value(value: Any, expected: Any) -> bool:
    if value == expected:
        return True
    if isinstance(value, dict):
        return any(find_nested_value(item, expected) for item in value.values())
    if isinstance(value, list):
        return any(find_nested_value(item, expected) for item in value)
    return False


def assert_response_preserved_value(response_path: Path, expected: Any | None) -> None:
    if expected is None:
        return
    response = json.loads(response_path.read_text(encoding="utf-8"))
    if not find_nested_value(response, expected):
        raise RuntimeError(
            "approval response does not contain the submitted value unchanged; "
            "stop and inspect possible encoding damage"
        )


def submit(args: argparse.Namespace) -> dict[str, Any]:
    value = load_json_value(args)
    expected_value = copy.deepcopy(value)
    result = submit_main_agent_approval(
        args.work_dir,
        args.request_id,
        decision=args.decision,
        value=value,
        comment=args.comment or None,
    )
    response_path = result.get("response_path")
    if response_path:
        assert_response_preserved_value(Path(response_path), expected_value)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Submit LGWF approval payloads without passing non-ASCII JSON through the shell."
    )
    parser.add_argument("--lgwf", type=Path, default=default_lgwf_facade())
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--decision", choices=["approve", "reject"], required=True)
    parser.add_argument("--value-file", type=Path)
    parser.add_argument("--value-json-ascii")
    parser.add_argument("--value-json-base64")
    parser.add_argument("--comment", default="")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = submit(args)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
