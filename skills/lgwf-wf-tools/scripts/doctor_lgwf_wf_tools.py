from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from validate_registry import run_validation


FACADE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FACADE_ROOT.parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
REGISTRY_PATH = FACADE_ROOT / "registry.json"
ROOT_SKILL_MD = FACADE_ROOT / "SKILL.md"
MODULE_CONTRACT_PATH = FACADE_ROOT / "workflows" / "01-share" / "module-contract.md"
ENTRY_CONTRACT_PATH = FACADE_ROOT / "workflows" / "01-share" / "entry-contract.md"
VENDOR_ROOT = FACADE_ROOT / "vendor" / "lgwf-client-assist"
VENDOR_AGENTS_MD = VENDOR_ROOT / "AGENTS.md"
VENDOR_SKILL_MD = VENDOR_ROOT / "SKILL.md"
LGWF_PY = VENDOR_ROOT / "scripts" / "lgwf.py"
WHEEL_GLOB = "lgwf-*.whl"
OUTPUT_TAIL_LIMIT = 4000
DOCTOR_LOCAL_DIR = FACADE_ROOT / ".local" / "doctor"


def summarize_output(text: str) -> dict[str, Any]:
    return {
        "length": len(text),
        "truncated": len(text) > OUTPUT_TAIL_LIMIT,
        "tail": text[-OUTPUT_TAIL_LIMIT:],
    }


def run_command(
    args: list[str],
    *,
    cwd: Path,
    artifact_dir: Path | None = None,
    artifact_stem: str | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=120)
    result = {
        "args": args,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": summarize_output(completed.stdout),
        "stderr": summarize_output(completed.stderr),
    }
    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe_artifact_stem(artifact_stem or "command")
        stdout_path = artifact_dir / f"{stem}.stdout.txt"
        stderr_path = artifact_dir / f"{stem}.stderr.txt"
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        result["artifacts"] = {
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        }
    return result


def _safe_artifact_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return stem or "artifact"


def check_path(label: str, path: Path, *, should_exist: bool = True) -> dict[str, Any]:
    exists = path.exists()
    passed = exists if should_exist else not exists
    return {
        "label": label,
        "passed": passed,
        "path": str(path),
        "exists": exists,
        "expected": "exists" if should_exist else "absent",
    }


def run_module_contract_validation() -> dict[str, Any]:
    failures: list[dict[str, Any]] = []

    if not MODULE_CONTRACT_PATH.is_file():
        failures.append({"label": "module_contract.exists", "path": str(MODULE_CONTRACT_PATH)})
    else:
        contract_text = MODULE_CONTRACT_PATH.read_text(encoding="utf-8")
        for token in ("codex_skill", "lgwf_workflow_package", "tool_workflow"):
            if token not in contract_text:
                failures.append({"label": "module_contract.type_declared", "token": token})
        for topic in ("模块定位", "入口", "依赖", "状态", "产物", "验证", "禁止"):
            if topic not in contract_text:
                failures.append({"label": "module_contract.topic_declared", "topic": topic})

    if not ENTRY_CONTRACT_PATH.is_file():
        failures.append({"label": "entry_contract.exists", "path": str(ENTRY_CONTRACT_PATH)})
    else:
        entry_contract_text = ENTRY_CONTRACT_PATH.read_text(encoding="utf-8")
        for token in ("input_mode", "auto_human_policy", "entry_contract.json"):
            if token not in entry_contract_text:
                failures.append({"label": "entry_contract.token_declared", "token": token})

    if SKILLS_ROOT.is_dir():
        for skill_root in sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir()):
            skill_name = skill_root.name
            for filename in ("SKILL.md", "AGENTS.md", "README.md"):
                if not (skill_root / filename).is_file():
                    failures.append({"label": "skill.entry_doc.exists", "skill": skill_name, "file": filename})
            agents_path = skill_root / "AGENTS.md"
            if agents_path.is_file():
                agents_text = agents_path.read_text(encoding="utf-8")
                for topic in ("模块类型", "模块定位", "入口", "依赖", "状态边界", "验证", "禁止事项"):
                    if topic not in agents_text:
                        failures.append({"label": "skill.agents.topic_declared", "skill": skill_name, "topic": topic})
            if (skill_root / "wf").is_dir():
                if not (skill_root / "wf" / "workflow.lgwf").is_file():
                    failures.append({"label": "skill.workflow.entry_exists", "skill": skill_name})
                if not (skill_root / "ws").is_dir():
                    failures.append({"label": "skill.workflow.work_dir_exists", "skill": skill_name})

    if REGISTRY_PATH.is_file():
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
        for workflow in registry.get("workflows", []):
            workflow_id = workflow.get("id")
            kind = workflow.get("kind")
            agents_md = workflow.get("agents_md")
            agents_path = FACADE_ROOT / str(agents_md)
            if not agents_path.is_file():
                failures.append({"label": "workflow.agents.exists", "workflow": workflow_id, "path": str(agents_md)})
                continue
            agents_text = agents_path.read_text(encoding="utf-8")
            if "module-contract.md" not in agents_text:
                failures.append({"label": "workflow.agents.module_contract_ref", "workflow": workflow_id})
            expected_type = "lgwf_workflow_package" if kind == "lgwf" else "tool_workflow"
            if expected_type not in agents_text:
                failures.append(
                    {
                        "label": "workflow.agents.module_type_declared",
                        "workflow": workflow_id,
                        "expected": expected_type,
                    }
                )

    return {
        "label": "module_contracts",
        "passed": not failures,
        "failures": failures,
    }


def _new_doctor_run_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = DOCTOR_LOCAL_DIR / "runs" / timestamp
    suffix = 1
    while run_dir.exists():
        run_dir = DOCTOR_LOCAL_DIR / "runs" / f"{timestamp}-{suffix:02d}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _persist_workflow_audit_payload(
    check: dict[str, Any],
    *,
    workflow_id: str,
    audit_dir: Path,
) -> None:
    artifacts = check.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    stdout_path = artifacts.get("stdout")
    if not isinstance(stdout_path, str):
        return
    try:
        payload = json.loads(Path(stdout_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{_safe_artifact_stem(workflow_id)}.json"
    audit_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts["audit_json"] = str(audit_path)


def _persist_doctor_result(result: dict[str, Any], run_dir: Path) -> dict[str, str]:
    DOCTOR_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    doctor_json = run_dir / "doctor.json"
    doctor_md = run_dir / "doctor.md"
    latest_json = DOCTOR_LOCAL_DIR / "latest.json"
    latest_md = DOCTOR_LOCAL_DIR / "latest.md"
    artifacts = {
        "run_dir": str(run_dir),
        "doctor_json": str(doctor_json),
        "doctor_md": str(doctor_md),
        "latest_json": str(latest_json),
        "latest_md": str(latest_md),
    }
    result["artifacts"] = artifacts
    doctor_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    doctor_md.write_text(_render_doctor_markdown(result), encoding="utf-8")
    shutil.copyfile(doctor_json, latest_json)
    shutil.copyfile(doctor_md, latest_md)
    return artifacts


def _render_doctor_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# lgwf-wf-tools deep health check",
        "",
        f"- passed: `{str(result.get('passed')).lower()}`",
        f"- facade_root: `{result.get('facade_root')}`",
        f"- client_root: `{result.get('client_root')}`",
        f"- deep: `{str(result.get('deep')).lower()}`",
    ]
    artifacts = result.get("artifacts")
    if isinstance(artifacts, dict):
        lines.extend(
            [
                f"- run_dir: `{artifacts.get('run_dir')}`",
                f"- full_json: `{artifacts.get('doctor_json')}`",
            ]
        )

    failed_checks = [item for item in result.get("checks", []) if not item.get("passed")]
    failed_deep_checks = [item for item in result.get("deep_checks", []) if not item.get("passed")]
    lines.extend(["", "## 失败概览", ""])
    if not failed_checks and not failed_deep_checks:
        lines.append("- 未发现失败项。")
    for item in failed_checks:
        lines.append(f"- `{item.get('label')}`")
    for item in failed_deep_checks:
        label = item.get("label")
        returncode = item.get("returncode")
        if returncode is None:
            lines.append(f"- `{label}`")
        else:
            lines.append(f"- `{label}` returncode=`{returncode}`")

    lines.extend(["", "## Workflow Audit Diagnostics", ""])
    workflow_items = [
        item
        for item in result.get("deep_checks", [])
        if str(item.get("label", "")).startswith("workflow_audit.")
    ]
    if not workflow_items:
        lines.append("- 未运行 workflow audit。")
    for item in workflow_items:
        _append_workflow_audit_markdown(lines, item)

    lines.extend(["", "## 命令产物", ""])
    for item in result.get("deep_checks", []):
        artifacts = item.get("artifacts")
        if not isinstance(artifacts, dict):
            continue
        lines.append(f"- `{item.get('label')}`")
        for key in ("audit_json", "stdout", "stderr"):
            if key in artifacts:
                lines.append(f"  - {key}: `{artifacts[key]}`")
    lines.append("")
    return "\n".join(lines)


def _append_workflow_audit_markdown(lines: list[str], item: dict[str, Any]) -> None:
    label = str(item.get("label", "workflow_audit"))
    artifacts = item.get("artifacts")
    audit_json = artifacts.get("audit_json") if isinstance(artifacts, dict) else None
    lines.append(f"### {label}")
    lines.append("")
    if not isinstance(audit_json, str):
        lines.append("- 未能解析完整 audit JSON；请查看 stdout/stderr 产物。")
        lines.append("")
        return
    try:
        payload = json.loads(Path(audit_json).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        lines.append(f"- audit_json 读取失败：`{audit_json}`")
        lines.append("")
        return
    lines.append(f"- passed: `{str(payload.get('passed')).lower()}`")
    lines.append(f"- workflow: `{payload.get('workflow', {}).get('name')}`")
    lines.append(f"- input: `{payload.get('input')}`")
    lines.append(f"- summary: {payload.get('summary')}")
    diagnostics = payload.get("diagnostics", [])
    if not diagnostics:
        lines.append("- diagnostics: none")
        lines.append("")
        return
    lines.append("- diagnostics:")
    for diagnostic in diagnostics:
        lines.append(
            "  - "
            f"`{diagnostic.get('severity')}` "
            f"`{diagnostic.get('code')}` "
            f"`{diagnostic.get('location')}`"
        )
        lines.append(f"    - {diagnostic.get('message')}")
        suggestion = diagnostic.get("suggestion")
        if suggestion:
            lines.append(f"    - suggestion: {suggestion}")
    lines.append("")


def run_doctor(*, deep: bool = False) -> dict[str, Any]:
    checks = [
        check_path("root_skill_md", ROOT_SKILL_MD),
        check_path("registry_json", REGISTRY_PATH),
        check_path("vendor_agents_md", VENDOR_AGENTS_MD),
        check_path("vendor_lgwf_py", LGWF_PY),
        check_path("vendor_skill_md_absent", VENDOR_SKILL_MD, should_exist=False),
    ]

    wheels = sorted((VENDOR_ROOT / "assets").glob(WHEEL_GLOB))
    checks.append(
        {
            "label": "vendor_wheel",
            "passed": bool(wheels),
            "path": str(VENDOR_ROOT / "assets" / WHEEL_GLOB),
            "matches": [str(path) for path in wheels],
            "expected": "at least one bundled wheel",
        }
    )

    registry = run_validation()
    checks.append(
        {
            "label": "registry_validation",
            "passed": bool(registry["passed"]),
            "details": registry,
        }
    )

    deep_checks: list[dict[str, Any]] = []
    run_dir: Path | None = _new_doctor_run_dir() if deep else None
    if deep and LGWF_PY.is_file():
        command_dir = run_dir / "commands" if run_dir is not None else None
        audit_dir = run_dir / "workflow-audits" if run_dir is not None else None
        deep_checks.append(run_module_contract_validation())
        deep_checks.append(
            {
                "label": "bundled_client_doctor",
                **run_command(
                    [sys.executable, str(LGWF_PY), "doctor"],
                    cwd=FACADE_ROOT,
                    artifact_dir=command_dir,
                    artifact_stem="bundled_client_doctor",
                ),
            }
        )
        if registry.get("passed"):
            registry_data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
            for item in registry_data.get("workflows", []):
                if item.get("kind", "lgwf") != "lgwf":
                    continue
                workflow_lgwf = FACADE_ROOT / item["workflow_lgwf"]
                workflow_id = str(item["id"])
                audit_check = {
                    "label": f"workflow_audit.{workflow_id}",
                    **run_command(
                        [sys.executable, str(LGWF_PY), "audit", str(workflow_lgwf)],
                        cwd=FACADE_ROOT,
                        artifact_dir=command_dir,
                        artifact_stem=f"workflow_audit.{workflow_id}",
                    ),
                }
                if audit_dir is not None:
                    _persist_workflow_audit_payload(
                        audit_check,
                        workflow_id=workflow_id,
                        audit_dir=audit_dir,
                    )
                deep_checks.append(audit_check)

    passed = all(bool(item["passed"]) for item in checks) and all(bool(item["passed"]) for item in deep_checks)
    result = {
        "passed": passed,
        "facade_root": str(FACADE_ROOT),
        "client_root": str(VENDOR_ROOT),
        "lgwf_py": str(LGWF_PY),
        "checks": checks,
        "deep": deep,
    }
    if deep:
        result["deep_checks"] = deep_checks
    if run_dir is not None:
        _persist_doctor_result(result, run_dir)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Check lgwf-wf-tools facade health.")
    parser.add_argument("--deep", action="store_true", help="also run bundled client doctor and internal workflow audits")
    args = parser.parse_args()

    result = run_doctor(deep=args.deep)
    print(json.dumps(result, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"doctor_lgwf_wf_tools failed: {exc}", file=sys.stderr)
        raise
