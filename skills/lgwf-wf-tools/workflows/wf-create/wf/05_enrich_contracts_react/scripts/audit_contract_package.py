"""检查目标 package 的 Contract 文档，并运行 lgwf.py audit。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS = ("模块定位", "入口", "依赖", "状态边界", "产物", "验证", "禁止事项")
CONTRACT_DOCS = ("AGENTS.md", "README.md")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_workspace_root(work_dir: Path, implementation_context: dict[str, Any]) -> Path:
    raw = str(implementation_context.get("workspace_root", "")).strip()
    if raw:
        candidate = Path(raw).resolve()
        if candidate.exists():
            return candidate
    current = work_dir.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists() or (candidate / "skills").is_dir():
            return candidate
    raise RuntimeError(f"无法从运行目录推导 workspace_root: {work_dir}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def check_contract_docs(target_abs: Path) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    combined_text = ""
    for doc_name in CONTRACT_DOCS:
        doc_path = target_abs / doc_name
        exists = doc_path.is_file()
        checks.append({"check": f"{doc_name} exists", "path": str(doc_path), "ok": exists})
        if not exists:
            failures.append(f"缺少 Contract 入口文档: {doc_name}")
            continue
        combined_text += "\n" + read_text(doc_path)

    for section in REQUIRED_SECTIONS:
        ok = section in combined_text
        checks.append({"check": f"contract section {section}", "ok": ok})
        if not ok:
            failures.append(f"Contract 文档缺少段落: {section}")
    return checks, failures


def run_lgwf_audit(workflow_lgwf: Path, workspace_root: Path) -> dict[str, Any]:
    # observe 阶段必须运行 lgwf.py audit，目标是 authoring audit pass。
    lgwf_py = workspace_root / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
    if not lgwf_py.exists():
        return {
            "ok": False,
            "skipped": True,
            "exit_code": None,
            "stdout": "",
            "stderr": f"找不到 lgwf.py: {lgwf_py}",
        }
    completed = subprocess.run(
        [sys.executable, str(lgwf_py), "audit", str(workflow_lgwf)],
        cwd=workspace_root,
        text=True,
        capture_output=True,
    )
    return {
        "ok": completed.returncode == 0,
        "skipped": False,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def audit_contract_package(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    contract_result = read_json(lgwf_dir / "contract_enrichment_result.json")
    workspace_root = find_workspace_root(work_dir, implementation_context)
    target_package_abs = str(
        contract_result.get("target_package_abs")
        or implementation_context.get("target_package_abs")
        or ""
    ).strip()
    target_abs = Path(target_package_abs).resolve() if target_package_abs else workspace_root

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    target_exists = target_abs.is_dir()
    checks.append({"check": "target_package_abs exists", "path": str(target_abs), "ok": target_exists})
    if not target_exists:
        failures.append(f"目标 package 不存在: {target_abs}")

    contract_checks, contract_failures = check_contract_docs(target_abs)
    checks.extend(contract_checks)
    failures.extend(contract_failures)

    workflow_lgwf = target_abs / "wf" / "workflow.lgwf"
    workflow_exists = workflow_lgwf.is_file()
    checks.append({"check": "wf/workflow.lgwf exists", "path": str(workflow_lgwf), "ok": workflow_exists})
    if not workflow_exists:
        failures.append(f"缺少目标 workflow: {workflow_lgwf}")

    audit = {"ok": False, "skipped": True, "exit_code": None, "stdout": "", "stderr": ""}
    if workflow_exists:
        audit = run_lgwf_audit(workflow_lgwf, workspace_root)
        checks.append({"check": "lgwf.py audit", "path": str(workflow_lgwf), "ok": audit.get("ok")})
        if not audit.get("ok"):
            failures.append("lgwf.py audit 未通过")

    result = {
        "passed": not failures,
        "target_package_root": implementation_context.get("target_package_root", ""),
        "target_package_abs": str(target_abs),
        "checks": checks,
        "audit": audit,
        "failures": failures,
    }
    write_json(lgwf_dir / "contract_audit_result.json", result)
    write_json(lgwf_dir / "contract_observe.json", result)
    return result


def main() -> None:
    result = audit_contract_package(Path.cwd())
    print(json.dumps({"lgwf_wf_create.contract_audit_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
