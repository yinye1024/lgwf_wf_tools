from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from validate_registry import run_validation


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"
ROOT_SKILL_MD = FACADE_ROOT / "SKILL.md"
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
        deep_checks.append({"label": "bundled_client_doctor", **run_command([sys.executable, str(LGWF_PY), "doctor"], cwd=FACADE_ROOT)})
        if registry.get("passed"):
            registry_data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))
            for item in registry_data.get("workflows", []):
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
