from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = SELF_IMPROVE_ROOT.parent
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "reports"
REGISTRY_PATH = FACADE_ROOT / "registry.json"
BASELINE_PATH = SELF_IMPROVE_ROOT / "workflow-health" / "baseline.json"


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


def workflow_root_from_registry(root: Path, workflow_lgwf: Any, agents_md: Any) -> Path:
    if isinstance(agents_md, str) and agents_md:
        return path_for(root, agents_md).parent
    if isinstance(workflow_lgwf, str) and workflow_lgwf:
        return path_for(root, workflow_lgwf).parent
    return root


def check_workflow(item: dict[str, Any], baseline: dict[str, dict[str, Any]], *, facade_root: Path) -> dict[str, Any]:
    workflow_id = str(item.get("id") or "<missing>")
    issues: list[str] = []
    workflow_lgwf = item.get("workflow_lgwf")
    agents_md = item.get("agents_md")
    work_dir = item.get("work_dir")
    workflow_root = workflow_root_from_registry(facade_root, workflow_lgwf, agents_md)

    if workflow_id not in baseline:
        issues.append("missing workflow-health baseline entry")

    if not isinstance(workflow_lgwf, str) or not workflow_lgwf:
        issues.append("missing workflow_lgwf")
    else:
        workflow_path = path_for(facade_root, workflow_lgwf)
        if not workflow_path.is_file():
            issues.append(f"workflow_lgwf missing: {workflow_lgwf}")

    agents_text = ""
    if not isinstance(agents_md, str) or not agents_md:
        issues.append("missing agents_md")
    else:
        agents_path = path_for(facade_root, agents_md)
        if not agents_path.is_file():
            issues.append(f"agents_md missing: {agents_md}")
        else:
            agents_text = agents_path.read_text(encoding="utf-8")

    if not isinstance(work_dir, str) or not work_dir:
        issues.append("missing work_dir")
    else:
        work_path = path_for(facade_root, work_dir)
        if work_path.resolve() == workflow_root.resolve():
            issues.append("work_dir must not equal workflow root")
        if "ws" not in work_path.name.lower():
            issues.append("work_dir should be an explicit ws directory")

    skill_files = sorted(path.relative_to(workflow_root).as_posix() for path in workflow_root.rglob("SKILL.md")) if workflow_root.exists() else []
    if skill_files:
        issues.append(f"internal workflow must not contain SKILL.md: {skill_files}")

    tests_dir = workflow_root / "tests"
    if not tests_dir.is_dir():
        issues.append("workflow tests directory missing")

    baseline_item = baseline.get(workflow_id, {})
    for key in ("audit_command", "test_command", "expected_role"):
        if not baseline_item.get(key):
            issues.append(f"baseline missing {key}")
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
    }


def build_report(
    workflow_id: str | None = None,
    *,
    facade_root: Path = FACADE_ROOT,
    registry_path: Path = REGISTRY_PATH,
    baseline_path: Path = BASELINE_PATH,
) -> dict[str, Any]:
    baseline = baseline_by_id(baseline_path)
    workflows = registry_workflows(registry_path)
    if workflow_id:
        workflows = [item for item in workflows if item.get("id") == workflow_id]
        if not workflows:
            raise ValueError(f"workflow id not found in registry: {workflow_id}")
    results = [check_workflow(item, baseline, facade_root=facade_root) for item in workflows]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow_id or "",
        "passed": all(item["passed"] for item in results),
        "workflow_count": len(results),
        "workflow_results": results,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# lgwf-wf-agent Workflow Health {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- workflow_count: `{report['workflow_count']}`",
        "",
    ]
    for item in report["workflow_results"]:
        marker = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{marker}` `{item['id']}`")
        for issue in item["issues"]:
            lines.append(f"  - {issue}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-id")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--facade-root", default=str(FACADE_ROOT), help="Facade root. Intended for tests and local diagnostics.")
    parser.add_argument("--registry", default=str(REGISTRY_PATH), help="registry.json path. Intended for tests and local diagnostics.")
    parser.add_argument("--baseline", default=str(BASELINE_PATH), help="workflow-health baseline path. Intended for tests and local diagnostics.")
    args = parser.parse_args()

    report = build_report(
        args.workflow_id,
        facade_root=Path(args.facade_root),
        registry_path=Path(args.registry),
        baseline_path=Path(args.baseline),
    )
    suffix = f"-{args.workflow_id}" if args.workflow_id else ""
    base = Path(args.output_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-workflow-health{suffix}"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"passed": report["passed"], "json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
