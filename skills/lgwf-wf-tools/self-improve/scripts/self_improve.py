from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = SELF_IMPROVE_ROOT / "manifest.json"


def load_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("self-improve manifest must be a JSON object")
    return data


def print_usage(manifest: dict[str, Any]) -> None:
    commands = manifest.get("commands", {})
    print("usage: python self-improve/scripts/self_improve.py <command> [args...]")
    print("")
    print("commands:")
    for name in sorted(commands):
        print(f"  {name}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    manifest = load_manifest()
    if not args or args[0] in {"-h", "--help", "help"}:
        print_usage(manifest)
        return 0

    command = args.pop(0)
    commands = manifest.get("commands")
    if not isinstance(commands, dict) or command not in commands:
        print(f"unknown self-improve command: {command}", file=sys.stderr)
        print_usage(manifest)
        return 2

    script = SELF_IMPROVE_ROOT / str(commands[command])
    if not script.is_file():
        print(f"self-improve command script missing: {script}", file=sys.stderr)
        return 2

    completed = subprocess.run([sys.executable, str(script), *args], cwd=SELF_IMPROVE_ROOT.parent)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
