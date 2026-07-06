from __future__ import annotations

import argparse
import json
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


def summarize_output(text: str) -> dict[str, Any]:
    return {
        "length": len(text),
        "truncated": len(text) > OUTPUT_TAIL_LIMIT,
        "tail": text[-OUTPUT_TAIL_LIMIT:],
    }


def run_command(args: list[str], *, cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=120)
    return {
        "args": args,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": summarize_output(completed.stdout),
        "stderr": summarize_output(completed.stderr),
    }


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
    if deep and LGWF_PY.is_file():
        deep_checks.append(run_module_contract_validation())
        deep_checks.append({"label": "bundled_client_doctor", **run_command([sys.executable, str(LGWF_PY), "doctor"], cwd=FACADE_ROOT)})
        if registry.get("passed"):
            registry_data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
            for item in registry_data.get("workflows", []):
                if item.get("kind", "lgwf") != "lgwf":
                    continue
                workflow_lgwf = FACADE_ROOT / item["workflow_lgwf"]
                deep_checks.append(
                    {
                        "label": f"workflow_audit.{item['id']}",
                        **run_command([sys.executable, str(LGWF_PY), "audit", str(workflow_lgwf)], cwd=FACADE_ROOT),
                    }
                )

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
