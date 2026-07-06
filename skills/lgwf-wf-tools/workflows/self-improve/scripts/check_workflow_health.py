from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "reports"
REGISTRY_PATH = FACADE_ROOT / "registry.json"
BASELINE_PATH = SELF_IMPROVE_ROOT / "workflow-health" / "baseline.json"
IGNORED_SKILL_SCAN_PARTS = {".git", ".hg", ".local", ".lgwf", "__pycache__"}
OUTPUT_TAIL_LIMIT = 2000


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def registry_workflows(registry_path: Path) -> list[dict[str, Any]]:
    data = read_json(registry_path)
    workflows = data.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("registry.json workflows must be list")
    return [item for item in workflows if isinstance(item, dict)]


def baseline_by_id(baseline_path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(baseline_path)
    workflows = data.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("workflow-health baseline workflows must be list")
    return {str(item.get("id")): item for item in workflows if isinstance(item, dict)}


def path_for(root: Path, relative: str) -> Path:
    return root / relative


def normalize_python_command(command: str) -> str:
    stripped = command.strip()
    if stripped == "python":
        return f'"{sys.executable}"'
    if stripped.startswith("python "):
        return f'"{sys.executable}" {stripped[len("python "):]}'
    return command


def output_tail(value: str) -> dict[str, Any]:
    return {
        "length": len(value),
        "truncated": len(value) > OUTPUT_TAIL_LIMIT,
        "tail": value[-OUTPUT_TAIL_LIMIT:],
    }


def workflow_root_from_registry(root: Path, workflow_lgwf: Any, agents_md: Any) -> Path:
    if isinstance(agents_md, str) and agents_md:
        return path_for(root, agents_md).parent
    if isinstance(workflow_lgwf, str) and workflow_lgwf:
        return path_for(root, workflow_lgwf).parent
    return root


def registered_workflow_roots(workflows: list[dict[str, Any]], *, facade_root: Path) -> set[Path]:
    roots: set[Path] = set()
    for item in workflows:
        if item.get("kind", "lgwf") != "lgwf":
            continue
        root = workflow_root_from_registry(facade_root, item.get("workflow_lgwf"), item.get("agents_md"))
        roots.add(root.resolve())
    return roots


def discover_unregistered_workflow_candidates(
    workflows: list[dict[str, Any]],
    *,
    facade_root: Path,
) -> list[dict[str, str]]:
    workflows_root = facade_root / "workflows"
    if not workflows_root.is_dir():
        return []
    registered_roots = registered_workflow_roots(workflows, facade_root=facade_root)
    candidates: list[dict[str, str]] = []
    for workflow_file in sorted(workflows_root.glob("*/workflow.lgwf")) + sorted(workflows_root.glob("*/wf/workflow.lgwf")):
        package_root = workflow_file.parent if workflow_file.parent.name != "wf" else workflow_file.parent.parent
        if package_root.resolve() in registered_roots:
            continue
        agents_md = package_root / "AGENTS.md"
        if not agents_md.is_file():
            continue
        candidates.append(
            {
                "id": package_root.name,
                "workflow_lgwf": workflow_file.relative_to(facade_root).as_posix(),
                "agents_md": agents_md.relative_to(facade_root).as_posix(),
            }
        )
    return candidates


def check_workflow(
    item: dict[str, Any],
    baseline: dict[str, dict[str, Any]],
    *,
    facade_root: Path,
    audit_timeout_seconds: int,
) -> dict[str, Any]:
    workflow_id = str(item.get("id") or "<missing>")
    issues: list[str] = []
    kind = item.get("kind", "lgwf")
    workflow_lgwf = item.get("workflow_lgwf")
    agents_md = item.get("agents_md")
    work_dir = item.get("work_dir")
    entry = item.get("entry")
    workflow_root = workflow_root_from_registry(facade_root, workflow_lgwf, agents_md)

    if workflow_id not in baseline:
        issues.append("missing workflow-health baseline entry")

    if kind not in {"lgwf", "tool-workflow"}:
        issues.append(f"unsupported workflow kind: {kind}")

    if kind == "lgwf":
        if not isinstance(workflow_lgwf, str) or not workflow_lgwf:
            issues.append("missing workflow_lgwf")
        else:
            workflow_path = path_for(facade_root, workflow_lgwf)
            if not workflow_path.is_file():
                issues.append(f"workflow_lgwf missing: {workflow_lgwf}")
    elif "workflow_lgwf" in item:
        issues.append("tool-workflow must not declare workflow_lgwf")

    agents_text = ""
    if not isinstance(agents_md, str) or not agents_md:
        issues.append("missing agents_md")
    else:
        agents_path = path_for(facade_root, agents_md)
        if not agents_path.is_file():
            issues.append(f"agents_md missing: {agents_md}")
        else:
            agents_text = agents_path.read_text(encoding="utf-8")

    if kind == "lgwf":
        if not isinstance(work_dir, str) or not work_dir:
            issues.append("missing work_dir")
        else:
            work_path = path_for(facade_root, work_dir)
            if work_path.resolve() == workflow_root.resolve():
                issues.append("work_dir must not equal workflow root")
            if "ws" not in work_path.name.lower():
                issues.append("work_dir should be an explicit ws directory")
    elif "work_dir" in item:
        issues.append("tool-workflow must not declare work_dir")

    if kind == "tool-workflow":
        if not isinstance(entry, str) or not entry:
            issues.append("missing entry")
        elif not path_for(facade_root, entry).is_file():
            issues.append(f"entry missing: {entry}")

    skill_files = (
        sorted(
            path.relative_to(workflow_root).as_posix()
            for path in workflow_root.rglob("SKILL.md")
            if not (set(path.relative_to(workflow_root).parts) & IGNORED_SKILL_SCAN_PARTS)
        )
        if workflow_root.exists()
        else []
    )
    if skill_files:
        issues.append(f"internal workflow must not contain SKILL.md: {skill_files}")

    tests_dir = workflow_root / "tests"
    if not tests_dir.is_dir():
        issues.append("workflow tests directory missing")

    if kind == "lgwf":
        required_self_improve = [
            "self-improve/manifest.json",
            "self-improve/scripts/self_improve.py",
            "self-improve/scripts/check_self_improve.py",
        ]
        for relative in required_self_improve:
            if not (workflow_root / relative).is_file():
                issues.append(f"self-improve module missing: {relative}")
        manifest_path = workflow_root / "self-improve" / "manifest.json"
        if manifest_path.is_file():
            manifest = read_json(manifest_path)
            if manifest.get("entrypoint") != "scripts/self_improve.py":
                issues.append("self-improve manifest entrypoint must be scripts/self_improve.py")
            if manifest.get("local_state_root") != ".local/self-improve":
                issues.append("self-improve manifest local_state_root must be .local/self-improve")

    baseline_item = baseline.get(workflow_id, {})
    audit_result: dict[str, Any] = {
        "passed": False,
        "returncode": 2,
        "command": "",
        "stdout": output_tail(""),
        "stderr": output_tail("missing audit_command"),
    }
    for key in ("audit_command", "test_command", "expected_role"):
        if not baseline_item.get(key):
            issues.append(f"baseline missing {key}")
    audit_command = baseline_item.get("audit_command")
    if isinstance(audit_command, str) and audit_command.strip():
        audit_result = run_audit_command(audit_command, facade_root=facade_root, timeout_seconds=audit_timeout_seconds)
        if not audit_result["passed"]:
            issues.append("audit command failed")
    semantic_requirements = baseline_item.get("semantic_requirements", [])
    if semantic_requirements is not None and not isinstance(semantic_requirements, list):
        issues.append("baseline semantic_requirements must be list")
    elif isinstance(semantic_requirements, list):
        for requirement in semantic_requirements:
            if not isinstance(requirement, dict):
                issues.append("semantic requirement must be object")
                continue
            requirement_id = str(requirement.get("id") or "<missing>")
            needles = requirement.get("any_contains", [])
            if not isinstance(needles, list) or not all(isinstance(item, str) for item in needles):
                issues.append(f"semantic requirement invalid any_contains: {requirement_id}")
                continue
            if agents_text and not any(needle in agents_text for needle in needles):
                issues.append(f"semantic requirement missing: {requirement_id}")

    return {
        "id": workflow_id,
        "passed": not issues,
        "issues": issues,
        "workflow_root": workflow_root.relative_to(facade_root).as_posix() if workflow_root.exists() else str(workflow_root),
        "baseline": baseline_item,
        "audit": audit_result,
    }


def run_audit_command(command: str, *, facade_root: Path, timeout_seconds: int) -> dict[str, Any]:
    normalized = normalize_python_command(command)
    try:
        completed = subprocess.run(
            normalized,
            cwd=facade_root,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "passed": completed.returncode == 0,
            "returncode": completed.returncode,
            "command": command,
            "stdout": output_tail(completed.stdout.strip()),
            "stderr": output_tail(completed.stderr.strip()),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "passed": False,
            "returncode": 124,
            "command": command,
            "stdout": output_tail(stdout.strip()),
            "stderr": output_tail((stderr.strip() + f"\naudit command timed out after {timeout_seconds}s").strip()),
        }
def build_report(
    workflow_id: str | None = None,
    *,
    facade_root: Path = FACADE_ROOT,
    registry_path: Path = REGISTRY_PATH,
    baseline_path: Path = BASELINE_PATH,
    audit_timeout_seconds: int = 120,
) -> dict[str, Any]:
    baseline = baseline_by_id(baseline_path)
    workflows = registry_workflows(registry_path)
    if workflow_id:
        workflows = [item for item in workflows if item.get("id") == workflow_id]
        if not workflows:
            raise ValueError(f"workflow id not found in registry: {workflow_id}")
    results = [
        check_workflow(item, baseline, facade_root=facade_root, audit_timeout_seconds=audit_timeout_seconds)
        for item in workflows
    ]
    unregistered_candidates = [] if workflow_id else discover_unregistered_workflow_candidates(workflows, facade_root=facade_root)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow_id or "",
        "passed": all(item["passed"] for item in results),
        "workflow_count": len(results),
        "workflow_results": results,
        "unregistered_workflow_candidates": unregistered_candidates,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# lgwf-wf-tools Workflow Health {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- workflow_count: `{report['workflow_count']}`",
        "",
    ]
    for item in report["workflow_results"]:
        marker = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{marker}` `{item['id']}`")
        audit = item.get("audit", {})
        if audit:
            audit_marker = "PASS" if audit.get("passed") else "FAIL"
            lines.append(f"  - audit: `{audit_marker}` returncode `{audit.get('returncode')}`")
        for issue in item["issues"]:
            lines.append(f"  - {issue}")
    candidates = report.get("unregistered_workflow_candidates", [])
    if candidates:
        lines.extend(["", "## Unregistered Workflow Candidates", ""])
        for item in candidates:
            lines.append(f"- `{item['id']}`: `{item['workflow_lgwf']}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-id")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--facade-root", default=str(FACADE_ROOT), help="Facade root. Intended for tests and local diagnostics.")
    parser.add_argument("--registry", default=str(REGISTRY_PATH), help="registry.json path. Intended for tests and local diagnostics.")
    parser.add_argument("--baseline", default=str(BASELINE_PATH), help="workflow-health baseline path. Intended for tests and local diagnostics.")
    parser.add_argument("--audit-timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    report = build_report(
        args.workflow_id,
        facade_root=Path(args.facade_root),
        registry_path=Path(args.registry),
        baseline_path=Path(args.baseline),
        audit_timeout_seconds=args.audit_timeout_seconds,
    )
    suffix = f"-{args.workflow_id}" if args.workflow_id else ""
    base = Path(args.output_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-workflow-health{suffix}"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"passed": report["passed"], "json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
