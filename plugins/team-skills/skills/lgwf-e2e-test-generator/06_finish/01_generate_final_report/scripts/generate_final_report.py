from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json, write_text


def optional_json(name: str) -> dict:
    return read_json(LGWF_DIR / name, default={})


def main() -> None:
    request = optional_json("e2e_target_request.normalized.json")
    coverage = optional_json("e2e_coverage_matrix.json")
    validations = {
        "script_flow": optional_json("e2e_script_flow_observe.json"),
        "runtime_fake": optional_json("e2e_runtime_fake_observe.json"),
        "real_positive": optional_json("e2e_real_positive_observe.json"),
    }
    generations = {
        "script_flow": optional_json("e2e_script_flow_generation.json"),
        "runtime_fake": optional_json("e2e_runtime_fake_generation.json"),
        "real_positive": optional_json("e2e_real_positive_generation.json"),
    }
    report = {
        "target": request,
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
        f"- 真实 Codex E2E 开关: `{request.get('real_codex_env', '')}`",
        "",
        "## 生成文件",
    ]
    for key, filename in request.get("generated_tests", {}).items():
        lines.append(f"- `{key}`: `{filename}`")
    lines.extend(["", "## 验收状态"])
    for key, data in validations.items():
        lines.append(f"- `{key}`: `{'passed' if data.get('passed') else 'pending_or_failed'}`")
    write_text(report_md, "\n".join(lines) + "\n")
    output_state({"final_report": {"report_json": report_json.as_posix(), "report_md": report_md.as_posix(), "generated": True}})


if __name__ == "__main__":
    main()
