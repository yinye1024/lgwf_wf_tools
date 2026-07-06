from __future__ import annotations

import subprocess
import sys

from _paths import SELF_IMPROVE_ROOT, WORKFLOW_ROOT


COMMANDS = {
    "incident": "record_incident.py",
    "proposal": "create_proposal.py",
    "scorecard": "generate_scorecard.py",
    "eval": "run_self_evals.py",
    "trace-eval": "run_trace_eval.py",
    "check": "check_self_improve.py",
}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        print("usage: python self-improve/scripts/self_improve.py <incident|proposal|scorecard|eval|trace-eval|check> [args...]")
        return 0 if args else 2
    command = args.pop(0)
    script_name = COMMANDS.get(command)
    if script_name is None:
        print(f"unknown self-improve command: {command}", file=sys.stderr)
        return 2
    script = SELF_IMPROVE_ROOT / "scripts" / script_name
    completed = subprocess.run([sys.executable, str(script), *args], cwd=WORKFLOW_ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
