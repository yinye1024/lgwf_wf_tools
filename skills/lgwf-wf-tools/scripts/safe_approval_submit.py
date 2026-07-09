from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
LGWF_PY = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def load_value(args: argparse.Namespace) -> dict[str, Any]:
    sources = [
        bool(args.value_file),
        bool(args.value_json_ascii),
        bool(args.value_json_base64),
    ]
    if sum(sources) != 1:
        raise ValueError("use exactly one of --value-file, --value-json-ascii, or --value-json-base64")
    if args.value_file:
        raw = Path(args.value_file).read_text(encoding="utf-8-sig")
    elif args.value_json_base64:
        raw = base64.b64decode(args.value_json_base64.encode("ascii")).decode("utf-8")
    else:
        raw = args.value_json_ascii
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("approval value must be a JSON object")
    return data


def build_command(args: argparse.Namespace, value: dict[str, Any]) -> list[str]:
    value_json = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    command = [
        sys.executable,
        str(LGWF_PY),
        args.kind,
        "submit",
        "--work-dir",
        args.work_dir,
        "--request-id",
        args.request_id,
    ]
    if args.kind == "approval":
        if not args.decision:
            raise ValueError("--decision is required for --kind approval")
        if args.decision == "approve":
            raise ValueError("approval approve does not accept value-json")
        command.extend(["--decision", args.decision])
    else:
        if not args.route:
            raise ValueError("--route is required for --kind review")
        if args.route != "revise":
            raise ValueError("only review revise accepts value-json")
        command.extend(["--route", args.route])
    command.extend(["--value-json", value_json])
    if args.comment:
        command.extend(["--comment", args.comment])
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit LGWF approval/review values without corrupting UTF-8 JSON.")
    parser.add_argument("--kind", choices=["approval", "review"], required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--decision", choices=["approve", "reject"])
    parser.add_argument("--route", choices=["approve", "revise", "reject"])
    parser.add_argument("--comment", default="")
    parser.add_argument("--value-file")
    parser.add_argument("--value-json-ascii")
    parser.add_argument("--value-json-base64")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        value = load_value(args)
        command = build_command(args, value)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"safe approval submit input error: {exc}", file=sys.stderr)
        return 2
    completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
