from __future__ import annotations

from pathlib import Path
import py_compile
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from e2e_generator_common import LGWF_DIR, output_state, read_json, write_json


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


def main() -> None:
    request = read_json(LGWF_DIR / "e2e_target_request.normalized.json")
    design = read_json(LGWF_DIR / "e2e_script_flow_design.json")
    generation = read_json(LGWF_DIR / "e2e_script_flow_generation.json")
    target_root = Path(request["workflow_root"])
    test_file = target_root / generation["test_file"]

    commands: list[dict[str, Any]] = []
    checks: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    coverage_gaps: list[dict[str, str]] = []

    try:
        py_compile.compile(str(test_file), doraise=True)
        checks["py_compile"] = {"passed": True, "evidence": str(test_file), "repair_hint": ""}
        commands.append(
            {
                "command": f"{sys.executable} -m py_compile {test_file}",
                "exit_code": 0,
                "stdout_summary": "",
                "stderr_summary": "",
            }
        )
    except Exception as exc:  # pragma: no cover - exercised by generated workflow failures.
        checks["py_compile"] = {
            "passed": False,
            "evidence": str(exc),
            "repair_hint": "修复生成的脚本级测试语法错误。",
        }
        issues.append("py_compile failed")
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
    checks["unittest"] = {
        "passed": unittest_result["exit_code"] == 0,
        "evidence": unittest_result["stdout_summary"] or unittest_result["stderr_summary"],
        "repair_hint": "" if unittest_result["exit_code"] == 0 else "根据失败断言修复生成测试或设计输入。",
    }
    if unittest_result["exit_code"] != 0:
        issues.append("unittest failed")

    source = test_file.read_text(encoding="utf-8") if test_file.exists() else ""
    forbidden = ["lgwf.py run", "--workflow-lgwf", "codex"]
    found = [pattern for pattern in forbidden if pattern in source]
    checks["no_runtime_launch"] = {
        "passed": not found,
        "evidence": "未发现 runtime/model 启动字面量。" if not found else ", ".join(found),
        "repair_hint": "" if not found else "移除脚本级测试中的 runtime 或真实模型启动逻辑。",
    }
    if found:
        issues.append("runtime/model launch pattern found")

    claimed = {item.get("coverage_ref") for item in generation.get("coverage", [])}
    expected = {item.get("coverage_ref") for item in design.get("coverage_claims", [])}
    missing = sorted(ref for ref in expected if ref and ref not in claimed)
    for ref in missing:
        coverage_gaps.append({"coverage_ref": str(ref), "source_of_gap": "generation", "details": "generation.coverage 缺少设计声明的覆盖项"})
    checks["coverage_alignment"] = {
        "passed": not missing,
        "evidence": f"expected={len(expected)} claimed={len(claimed)}",
        "repair_hint": "" if not missing else "补齐 e2e_script_flow_generation.json 的 coverage 映射。",
    }
    if missing:
        issues.append("coverage alignment failed")

    passed = all(item["passed"] for item in checks.values())
    observe = {
        "passed": passed,
        "issues": issues,
        "summary": "脚本级 E2E 验收通过。" if passed else "脚本级 E2E 验收失败。",
        "commands": commands,
        "coverage_gaps": coverage_gaps,
        "criterion_checks": checks,
    }
    write_json(LGWF_DIR / "e2e_script_flow_observe.json", observe)
    output_state({"script_flow_validation": observe})


if __name__ == "__main__":
    main()
