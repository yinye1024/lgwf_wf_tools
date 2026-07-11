from __future__ import annotations

import subprocess
import sys
from pathlib import Path


COMMANDS = {
    "check": "check_self_improve.py",
}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        print("usage: python self-improve/scripts/self_improve.py check")
        return 0 if args else 2
    command = args.pop(0)
    script_name = COMMANDS.get(command)
    if script_name is None:
        print(f"unknown self-improve command: {command}", file=sys.stderr)
        return 2
    script = Path(__file__).resolve().parent / script_name
    completed = subprocess.run([sys.executable, str(script), *args], cwd=Path(__file__).resolve().parents[2])
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
