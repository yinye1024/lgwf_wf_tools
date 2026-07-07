"""对 wf-create 生成出的目标 workflow 执行确定性 authoring audit。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


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


def audit_created_package(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    implementation_result = read_json(lgwf_dir / "implementation_result.json")
    workspace_root = find_workspace_root(work_dir, implementation_context)
    target_package_root = str(
        implementation_result.get("target_package_root")
        or implementation_context.get("target_package_root")
        or ""
    ).strip()
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    if not target_package_root:
        failures.append("缺少 target_package_root")
        target_abs = workspace_root
    else:
        target_abs = (workspace_root / target_package_root).resolve()
        try:
            target_abs.relative_to(workspace_root.resolve())
        except ValueError:
            failures.append(f"target_package_root 越界: {target_package_root}")

    workflow_lgwf = target_abs / "wf" / "workflow.lgwf"
    checks.append({"check": "target wf/workflow.lgwf exists", "path": str(workflow_lgwf), "ok": workflow_lgwf.exists()})
    if not workflow_lgwf.exists():
        failures.append(f"缺少目标 workflow: {workflow_lgwf}")

    lgwf_py = workspace_root / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
    checks.append({"check": "bundled lgwf.py exists", "path": str(lgwf_py), "ok": lgwf_py.exists()})
    audit: dict[str, Any] = {"ok": False, "skipped": True, "stdout": "", "stderr": "", "exit_code": None}
    if workflow_lgwf.exists() and lgwf_py.exists():
        completed = subprocess.run(
            [sys.executable, str(lgwf_py), "audit", str(workflow_lgwf)],
            cwd=workspace_root,
            text=True,
            capture_output=True,
        )
        audit = {
            "ok": completed.returncode == 0,
            "skipped": False,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        checks.append({"check": "lgwf.py audit", "path": str(workflow_lgwf), "ok": audit["ok"]})
        if not audit["ok"]:
            failures.append("lgwf.py audit 未通过")

    result = {
        "passed": not failures,
        "target_package_root": target_package_root,
        "target_package_abs": str(target_abs),
        "workflow_lgwf": str(workflow_lgwf),
        "checks": checks,
        "audit": audit,
        "failures": failures,
    }
    write_json(lgwf_dir / "implementation_audit_result.json", result)
    write_json(lgwf_dir / "implementation_observe.json", result)
    return result


def main() -> None:
    result = audit_created_package(Path.cwd())
    print(json.dumps({"lgwf_wf_create.implementation_audit_result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
