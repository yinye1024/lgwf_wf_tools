from __future__ import annotations

import argparse
import shutil
from pathlib import Path


RUNTIME_PATHS = (
    ".lgwf/react_task_request.json",
    ".lgwf/react_task_plan_reason.md",
    ".lgwf/react_task_plan_proposal.json",
    ".lgwf/react_task_plan_observe.json",
    ".lgwf/react_task_plan_generation_direction.json",
    ".lgwf/react_acceptance_reason.md",
    ".lgwf/react_acceptance_proposal.json",
    ".lgwf/react_acceptance_observe.json",
    ".lgwf/react_acceptance_generation_direction.json",
    ".lgwf/react_task_contract_approval.json",
    ".lgwf/react_task_plan.json",
    ".lgwf/react_acceptance_plan.json",
    ".lgwf/react_task_context.json",
    ".lgwf/react_task_input.json",
    ".lgwf/react_task_implementation_reason.md",
    ".lgwf/react_task_result.json",
    ".lgwf/react_task_history.json",
    ".lgwf/react_task_route.json",
    ".lgwf/react_task_max_attempt_decision.json",
    ".lgwf/max_attempt_decision.json",
    ".lgwf/react_task_max_attempt_approval.json",
    "reports/react-task",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", default=".")
    args = parser.parse_args()
    root = Path(args.package_root).resolve()
    for relative in RUNTIME_PATHS:
        path = root / relative
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    print(f"cleaned lgwf-plan runtime under {root}")


if __name__ == "__main__":
    main()

