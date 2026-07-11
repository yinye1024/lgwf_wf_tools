from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import (
    append_stage_result,
    finalize_stage_decision,
    generated_test_files,
    generated_tests_path,
    latest_stage_decision,
    lgwf_dir,
    load_target,
    output_state,
    read_json,
    target_package_root,
    write_json,
)


E2E_TYPE_TO_STAGE = {
    "script_flow": "script_flow_e2e",
    "runtime_fake": "runtime_fake_e2e",
    "real_positive": "real_positive_e2e",
    "wf_fix_positive": "wf_fix_positive_e2e",
}


def child_report_path() -> Path:
    return lgwf_dir() / "isolations/run_workflow/e2e_generate/work_dir/reports/e2e-test-generator/report.json"


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def materialize_generated_tests(target: dict[str, Any]) -> dict[str, Any]:
    report_path = child_report_path()
    generated_tests = generated_test_files(target)
    report = read_json(report_path, None)
    if not isinstance(report, dict):
        summary: dict[str, Any] = {
            "status": "no_child_report_existing_tests",
            "report_path": str(report_path),
            "source_root": "",
            "target_root": str(target_package_root(target).resolve()),
            "generated_tests": generated_tests,
            "copied": [],
            "missing": [],
            "skipped": [{"reason": "e2e-test-generator report not found; using existing generated test entries"}],
        }
        for stage_id in ("script_flow_e2e", "runtime_fake_e2e"):
            candidate = Path(generated_tests[stage_id]).resolve()
            if not candidate.is_file():
                summary["missing"].append({"stage_id": stage_id, "destination": str(candidate)})
        if summary["missing"]:
            summary["status"] = "missing_child_report_and_tests"
            write_json(lgwf_dir() / "post_fix_generated_tests.materialized.json", summary)
            write_json(generated_tests_path(), generated_tests)
            missing = ", ".join(item["stage_id"] for item in summary["missing"])
            raise FileNotFoundError(f"e2e-test-generator report not found and generated tests are missing: {missing}")
        write_json(lgwf_dir() / "post_fix_generated_tests.materialized.json", summary)
        write_json(generated_tests_path(), generated_tests)
        return summary

    child_target = report.get("target") if isinstance(report.get("target"), dict) else {}
    child_root_value = child_target.get("workflow_root")
    if not isinstance(child_root_value, str) or not child_root_value.strip():
        raise ValueError("e2e-test-generator report missing target.workflow_root")
    child_root = Path(child_root_value).expanduser().resolve()

    output_dir = child_target.get("test_output_dir") if isinstance(child_target.get("test_output_dir"), str) else "tests"
    generated = report.get("generated_tests")
    if not isinstance(generated, dict):
        generated = child_target.get("generated_tests") if isinstance(child_target.get("generated_tests"), dict) else {}

    selected = report.get("selected_test_types")
    if not isinstance(selected, list):
        selected = child_target.get("selected_test_types") if isinstance(child_target.get("selected_test_types"), list) else []

    destination_root = target_package_root(target).resolve()
    summary: dict[str, Any] = {
        "status": "copied",
        "report_path": str(report_path),
        "source_root": str(child_root),
        "target_root": str(destination_root),
        "generated_tests": generated_tests,
        "copied": [],
        "missing": [],
        "skipped": [],
    }

    for e2e_type in selected:
        if not isinstance(e2e_type, str):
            continue
        stage_id = E2E_TYPE_TO_STAGE.get(e2e_type)
        filename = generated.get(e2e_type)
        if not stage_id or not isinstance(filename, str) or not filename.strip():
            summary["skipped"].append({"test_type": e2e_type, "reason": "未找到可复制的生成文件名"})
            continue

        source = (child_root / str(output_dir) / filename).resolve()
        destination = Path(generated_tests[stage_id]).resolve()
        if not is_relative_to(source, child_root):
            raise ValueError(f"refusing to copy source outside child workflow root: {source}")
        if not is_relative_to(destination, destination_root):
            raise ValueError(f"refusing to write destination outside target package root: {destination}")
        if not source.is_file():
            summary["missing"].append({"test_type": e2e_type, "source": str(source), "destination": str(destination)})
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        summary["copied"].append({"test_type": e2e_type, "source": str(source), "destination": str(destination)})

    if summary["missing"]:
        summary["status"] = "partial"
        write_json(lgwf_dir() / "post_fix_generated_tests.materialized.json", summary)
        write_json(generated_tests_path(), generated_tests)
        missing = ", ".join(item["test_type"] for item in summary["missing"])
        raise FileNotFoundError(f"selected generated tests missing from child workspace: {missing}")
    if not summary["copied"]:
        summary["status"] = "no_selected_tests"

    write_json(lgwf_dir() / "post_fix_generated_tests.materialized.json", summary)
    write_json(generated_tests_path(), generated_tests)
    return summary


def write_non_run_materialization(target: dict[str, Any], status: str) -> dict[str, Any]:
    generated_tests = generated_test_files(target)
    summary: dict[str, Any] = {
        "status": status,
        "report_path": "",
        "source_root": "",
        "target_root": str(target_package_root(target).resolve()),
        "generated_tests": generated_tests,
        "copied": [],
        "missing": [],
        "skipped": [{"reason": f"e2e_generate route is {status}"}],
    }
    write_json(lgwf_dir() / "post_fix_generated_tests.materialized.json", summary)
    write_json(generated_tests_path(), generated_tests)
    return summary


def main() -> None:
    decision = latest_stage_decision("e2e_generate")
    if decision is None:
        decision = finalize_stage_decision("e2e_generate")
        append_stage_result("e2e_generate", decision["route"], decision=decision)

    route = "stop" if decision.get("route") == "stop" else "continue"
    updates: dict[str, Any] = {"e2e_generate_stage_route": route}
    target = load_target()
    if decision.get("route") == "run":
        updates["e2e_generate_materialized_tests"] = materialize_generated_tests(target)
    else:
        updates["e2e_generate_materialized_tests"] = write_non_run_materialization(
            target,
            str(decision.get("route") or "skipped"),
        )
    output_state(updates, next_key=route, route_node="e2e_generate_stage")


if __name__ == "__main__":
    main()
