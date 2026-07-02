from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json, write_text

TEST_TYPES = ("script_flow", "runtime_fake", "real_positive", "wf_fix_positive")


def optional_json(name: str) -> dict:
    return read_json(LGWF_DIR / name, default={})


def selected_types(request: dict) -> list[str]:
    return list(request.get("selected_test_types") or TEST_TYPES)


def result_for(name: str, data: dict, selected: set[str]) -> dict:
    if name not in selected:
        return {"status": "skipped", "passed": False}
    result = dict(data)
    result.setdefault("status", "passed" if result.get("passed") else "pending_or_failed")
    return result


def main() -> None:
    request = optional_json("e2e_target_request.normalized.json")
    coverage = optional_json("e2e_coverage_matrix.json")
    selected_list = selected_types(request)
    selected_set = set(selected_list)
    validations = {
        "script_flow": result_for("script_flow", optional_json("e2e_script_flow_observe.json"), selected_set),
        "runtime_fake": result_for("runtime_fake", optional_json("e2e_runtime_fake_observe.json"), selected_set),
        "real_positive": result_for("real_positive", optional_json("e2e_real_positive_observe.json"), selected_set),
        "wf_fix_positive": result_for("wf_fix_positive", optional_json("e2e_wf_fix_positive_observe.json"), selected_set),
    }
    generations = {
        "script_flow": result_for("script_flow", optional_json("e2e_script_flow_generation.json"), selected_set),
        "runtime_fake": result_for("runtime_fake", optional_json("e2e_runtime_fake_generation.json"), selected_set),
        "real_positive": result_for("real_positive", optional_json("e2e_real_positive_generation.json"), selected_set),
        "wf_fix_positive": result_for("wf_fix_positive", optional_json("e2e_wf_fix_positive_generation.json"), selected_set),
    }
    report = {
        "target": request,
        "selected_test_types": selected_list,
        "generated_tests": request.get("generated_tests", {}),
        "coverage_summary": {
            "script_contracts": len(coverage.get("script_flow", {}).get("script_contracts", [])),
            "routes": len(coverage.get("script_flow", {}).get("routes", [])),
            "codex_artifacts": len(coverage.get("runtime_fake", {}).get("output_json", [])),
        },
        "generations": generations,
        "validations": validations,
    }
    report_json = Path("reports/e2e-test-generator/report.json")
    report_md = Path("reports/e2e-test-generator/report.md")
    write_json(report_json, report)
    lines = [
        "# E2E 测试生成报告",
        "",
        f"- 目标 workflow: `{request.get('workflow_lgwf', '')}`",
        f"- 测试输出目录: `{request.get('test_output_dir', 'tests')}`",
        f"- 本次选择生成: `{', '.join(selected_list)}`",
        "- 真实 Codex E2E: 人工直接执行对应手动入口，文件名不以 `test_` 开头，默认不纳入 `unittest discover` 回归集合。",
        "- wf-fix 正向 E2E: 人工直接执行 `wf_fix_positive` 手动入口，复用真实正向场景启动 `wf-fix` 边跑边修复，不接入常规回归命令。",
        "",
        "## 生成文件",
    ]
    for key, filename in request.get("generated_tests", {}).items():
        status = "selected" if key in selected_set else "skipped"
        lines.append(f"- `{key}`: `{filename}` ({status})")
    lines.extend(["", "## 验收状态"])
    for key, data in validations.items():
        lines.append(f"- `{key}`: `{'passed' if data.get('passed') else 'pending_or_failed'}`")
    write_text(report_md, "\n".join(lines) + "\n")
    output_state({"final_report": {"report_json": report_json.as_posix(), "report_md": report_md.as_posix(), "generated": True}})


if __name__ == "__main__":
    main()
