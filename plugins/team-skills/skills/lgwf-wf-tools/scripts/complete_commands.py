from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_PATH = FACADE_ROOT / "commands.json"


def load_commands() -> list[dict[str, str]]:
    data = json.loads(COMMANDS_PATH.read_text(encoding="utf-8-sig"))
    commands = data.get("commands", [])
    if not isinstance(commands, list):
        return []
    result: list[dict[str, str]] = []
    for item in commands:
        if not isinstance(item, dict):
            continue
        command = item.get("command")
        description = item.get("description")
        if isinstance(command, str) and isinstance(description, str):
            result.append({"command": command, "description": description})
    return result


def complete(prefix: str) -> dict[str, Any]:
    normalized = prefix.strip()
    matches = [
        item
        for item in load_commands()
        if item["command"].casefold().startswith(normalized.casefold())
    ]
    return {"prefix": prefix, "matches": matches}


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = list(sys.argv[1:] if argv is None else argv)
    prefix = args[0] if args else ""
    print(json.dumps(complete(prefix), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"complete_commands failed: {exc}", file=sys.stderr)
        raise
