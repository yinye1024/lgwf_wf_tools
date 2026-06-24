from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target
from target_repair_loop import current_workspace_dir, write_current_artifact


EXCLUDED_DIRS = {".git", ".hg", ".svn", ".lgwf", "__pycache__", ".pytest_cache"}


def _ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDED_DIRS}


def _workflow_relative_to_package(package_root: Path, workflow: Path) -> Path:
    try:
        return workflow.resolve().relative_to(package_root.resolve())
    except ValueError as exc:
        raise ValueError(f"target_workflow_lgwf must be inside target_package_root: {workflow}") from exc


def prepare_candidate_workspace(lgwf_root: Path, target: dict[str, Any]) -> dict[str, Any]:
    package_root = Path(str(target.get("target_package_root") or "")).resolve()
    workflow = Path(str(target.get("target_workflow_lgwf") or package_root / "workflow.lgwf")).resolve()
    if not package_root.exists() or not package_root.is_dir():
        raise ValueError(f"target_package_root must be an existing directory: {package_root}")
    if not workflow.exists() or not workflow.is_file():
        raise ValueError(f"target_workflow_lgwf must be an existing file: {workflow}")

    workspace = current_workspace_dir(lgwf_root)
    if workspace.exists():
        shutil.rmtree(workspace)
    baseline = workspace / "baseline"
    candidate = workspace / "candidate"
    run_dir = workspace / "run"

    shutil.copytree(package_root, baseline, ignore=_ignore)
    shutil.copytree(baseline, candidate)
    run_dir.mkdir(parents=True, exist_ok=True)

    workflow_relative = _workflow_relative_to_package(package_root, workflow)
    candidate_workflow = candidate / workflow_relative
    data = {
        "source_package_root": str(package_root),
        "source_workflow_lgwf": str(workflow),
        "baseline_package_root": baseline.as_posix(),
        "candidate_package_root": candidate.as_posix(),
        "candidate_workflow_lgwf": candidate_workflow.as_posix(),
        "run_dir": run_dir.as_posix(),
        "target_dirs": [candidate.as_posix()],
        "target_files": [],
    }
    write_current_artifact(lgwf_root, "workspace", data)
    return data


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    workspace = prepare_candidate_workspace(root, target)
    append_history(
        {
            "event": "repair_agent_loop_prepared",
            "baseline": workspace["baseline_package_root"],
            "candidate": workspace["candidate_package_root"],
        }
    )
    print(
        json.dumps(
            {
                "lgwf_wf_fix.target_repair_workspace": workspace,
                "targets.dirs": workspace["target_dirs"],
                "targets.files": workspace["target_files"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
