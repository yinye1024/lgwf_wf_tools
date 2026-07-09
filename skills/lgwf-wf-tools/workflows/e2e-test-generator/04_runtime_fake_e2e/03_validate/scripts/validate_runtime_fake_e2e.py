from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, slugify, write_json


def summary(text: str, limit: int = 500) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def command_result(command: list[str], *, cwd: Path, timeout: int = 120) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": " ".join(command),
            "exit_code": completed.returncode,
            "stdout_summary": summary(completed.stdout),
            "stderr_summary": summary(completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "exit_code": -1,
            "stdout_summary": summary(exc.stdout if isinstance(exc.stdout, str) else ""),
            "stderr_summary": f"timeout after {timeout} seconds",
        }


def add_check(
    checks: dict[str, dict[str, Any]],
    issues: list[str],
    name: str,
    passed: bool,
    evidence: str,
    repair_hint: str,
) -> None:
    checks[name] = {
        "passed": passed,
        "evidence": evidence,
        "issue_code": "" if passed else f"runtime_fake:{name}",
        "source_location": ".lgwf/e2e_runtime_fake_generation.json",
        "repair_hint": "" if passed else repair_hint,
    }
    if not passed:
        issues.append(f"{name} failed")


def route_key(route: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(route.get("route_id") or ""),
        str(route.get("value") or ""),
        str(route.get("target") or ""),
        str(route.get("workflow") or "workflow.lgwf"),
    )


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    design = read_json(LGWF_DIR / "e2e_runtime_fake_design.json")
    generation = read_json(LGWF_DIR / "e2e_runtime_fake_generation.json")
    target_root = Path(request["workflow_root"])
    test_file = target_root / generation["test_file"]

    commands: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}
    scenario_checks: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    coverage_gaps: list[dict[str, Any]] = []

    if not bool(generation.get("generated")):
        observe = {
            "passed": True,
            "issues": [],
            "summary": "runtime_fake 未选中，跳过生成和校验。",
            "commands": [],
            "contract_checks": {"skipped": {"passed": True, "evidence": "generated=false", "repair_hint": ""}},
            "scenario_checks": {},
            "coverage_gaps": [],
        }
        write_json(LGWF_DIR / "e2e_runtime_fake_observe.json", observe)
        output_state({"runtime_fake_validation": observe})
        return

    try:
        py_compile.compile(str(test_file), doraise=True)
        add_check(checks, issues, "py_compile", True, str(test_file), "")
        commands.append(
            {
                "command": f"{sys.executable} -m py_compile {test_file}",
                "exit_code": 0,
                "stdout_summary": "",
                "stderr_summary": "",
            }
        )
    except Exception as exc:  # pragma: no cover - exercised by generated workflow failures.
        add_check(checks, issues, "py_compile", False, summary(str(exc)), "修复生成的 runtime fake 测试语法错误。")
        commands.append(
            {
                "command": f"{sys.executable} -m py_compile {test_file}",
                "exit_code": 1,
                "stdout_summary": "",
                "stderr_summary": summary(str(exc)),
            }
        )

    unittest_result = command_result([sys.executable, str(test_file)], cwd=target_root)
    commands.append(unittest_result)
    add_check(
        checks,
        issues,
        "unittest",
        unittest_result["exit_code"] == 0,
        unittest_result["stdout_summary"] or unittest_result["stderr_summary"],
        "根据生成测试失败断言修复 runtime fake 设计或生成逻辑。",
    )

    source = test_file.read_text(encoding="utf-8") if test_file.exists() else ""
    add_check(
        checks,
        issues,
        "run_command_present",
        "lgwf.py run --workflow-lgwf" in source,
        "检测 lgwf.py run --workflow-lgwf 字面量。",
        "生成测试必须保留 runtime 启动命令模板。",
    )
    add_check(
        checks,
        issues,
        "prompt_file_supported",
        "--prompt-file" in source,
        "检测 --prompt-file 字面量。",
        "Python fake Codex 必须通过 --prompt-file 读取 prompt。",
    )
    add_check(
        checks,
        issues,
        "python_fake_present",
        "class FakeCodex" in source and "Python fake Codex" in source,
        "检测 class FakeCodex 与 Python fake Codex 字面量。",
        "生成测试必须使用 Python fake Codex，不得依赖真实模型。",
    )
    no_js = "node_modules" not in source and "JS shim" not in source
    add_check(checks, issues, "no_js_shim", no_js, "检测 node_modules/JS shim 不存在。", "移除 JS shim 和 node_modules 依赖。")
    approval_driven = all(token in source for token in ("approval get", "approval submit", "status"))
    add_check(
        checks,
        issues,
        "approval_driven",
        approval_driven,
        "检测 approval get、approval submit 和 status 字面量。",
        "生成测试必须显式保留审批消费链和状态轮询契约。",
    )

    generated_methods = {item.get("test_method") for item in generation.get("scenario_generation", [])}
    for scenario in design.get("scenarios", []):
        scenario_id = str(scenario.get("scenario_id") or "")
        expected_method = f"test_{slugify(scenario_id)}"
        present = expected_method in source and expected_method in generated_methods
        scenario_checks[scenario_id] = {
            "passed": present,
            "evidence": expected_method,
            "issue_code": "" if present else "runtime_fake:missing_scenario_method",
            "source_location": str(test_file),
            "repair_hint": "" if present else "补齐 design.scenarios[] 对应的生成测试方法。",
        }
        if not present:
            issues.append(f"missing scenario method: {scenario_id}")

    expected_routes = {route_key(route) for route in design.get("branch_targets", [])}
    covered_routes: set[tuple[str, str, str, str]] = set()
    for scenario in design.get("scenarios", []):
        for route in scenario.get("covered_branches", []) or []:
            covered_routes.add(route_key(route))
    missing_routes = sorted(expected_routes - covered_routes)
    for route in missing_routes:
        coverage_gaps.append(
            {
                "kind": "business_route",
                "target": ":".join(route),
                "blocking": True,
                "reason": "design.scenarios[].covered_branches 未覆盖该 runtime route。",
            }
        )
    add_check(
        checks,
        issues,
        "business_route_coverage",
        not missing_routes,
        f"expected={len(expected_routes)} covered={len(covered_routes)}",
        "为每个 branch_targets/routes 分支生成独立 scenario 和测试方法。",
    )

    passed = all(item["passed"] for item in checks.values()) and all(item["passed"] for item in scenario_checks.values())
    observe = {
        "passed": passed,
        "issues": issues,
        "summary": "runtime fake E2E 验收通过。" if passed else "runtime fake E2E 验收失败。",
        "commands": commands,
        "contract_checks": checks,
        "scenario_checks": scenario_checks,
        "coverage_gaps": coverage_gaps,
    }
    write_json(LGWF_DIR / "e2e_runtime_fake_observe.json", observe)
    output_state({"runtime_fake_validation": observe})


if __name__ == "__main__":
    main()
