from __future__ import annotations

import argparse
import json
import fnmatch
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import validate_manifest


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = SELF_IMPROVE_ROOT.parent
DEFAULT_REPORT_DIR = FACADE_ROOT / ".local" / "self-improve" / "reports"
LOCAL_OVERRIDES = FACADE_ROOT / ".local" / "overrides"
OVERRIDE_SCHEMA = SELF_IMPROVE_ROOT / "overrides" / "schema.json"
SELF_EVAL_TRIGGER_PATTERNS = [
    "SKILL.md",
    "AGENTS.md",
    "registry.json",
    "workflows/*/AGENTS.md",
    "workflows/**/workflow.lgwf",
    "scripts/init_lgwf_wf_agent.py",
    "scripts/doctor_lgwf_wf_agent.py",
    "vendor/lgwf-client-assist/.lgwf-client-assist-vendor.json",
]
FORBIDDEN_OVERRIDE_TERMS = [
    "auto approve",
    "自动 approve",
    "跳过 approval",
    "skip approval",
    "direct write .response.json",
    "直接写 .response.json",
    "fallback 到用户 .codex",
    "fallback to user .codex",
]
ALLOWED_OVERRIDE_KEYS = {"additional_rules", "local_work_dirs", "experimental_workflows"}
ALLOWED_EXPERIMENTAL_WORKFLOW_KEYS = {"id", "workflow_lgwf", "work_dir", "agents_md", "description"}
REQUIRED_EXPERIMENTAL_WORKFLOW_KEYS = {"id", "workflow_lgwf", "work_dir", "agents_md"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_registry() -> dict[str, Any]:
    registry_path = FACADE_ROOT / "registry.json"
    data = read_json(registry_path)
    if not isinstance(data, dict):
        raise ValueError("registry.json must be a JSON object")
    return data


def registry_ids(registry: dict[str, Any]) -> set[str]:
    workflows = registry.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("registry.json must contain workflows list")
    ids: set[str] = set()
    for item in workflows:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.add(item["id"])
    return ids


def check_root_only_skill() -> list[str]:
    skill_files = sorted(path.relative_to(FACADE_ROOT).as_posix() for path in FACADE_ROOT.rglob("SKILL.md"))
    return [] if skill_files == ["SKILL.md"] else [f"expected only root SKILL.md, found {skill_files}"]


def check_registry_paths(registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    workflows = registry.get("workflows")
    if not isinstance(workflows, list):
        return ["registry.json workflows must be a list"]
    for item in workflows:
        if not isinstance(item, dict):
            issues.append("registry workflow entry must be object")
            continue
        workflow_id = item.get("id", "<missing>")
        for key in ("workflow_lgwf", "work_dir", "agents_md"):
            value = item.get(key)
            if not isinstance(value, str) or not value:
                issues.append(f"{workflow_id}: missing {key}")
                continue
            if key != "work_dir" and not (FACADE_ROOT / value).exists():
                issues.append(f"{workflow_id}: {key} does not exist: {value}")
    return issues


def validate_case(case: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    expected = case.get("expected")
    if not isinstance(expected, dict):
        return ["case expected must be object"]

    ids = registry_ids(registry)
    workflow_id = expected.get("workflow_id")
    if workflow_id is not None and workflow_id not in ids:
        issues.append(f"expected workflow_id not in registry: {workflow_id}")

    for path_text in expected.get("must_read", []) or []:
        if not isinstance(path_text, str) or not (FACADE_ROOT / path_text).exists():
            issues.append(f"must_read path missing: {path_text}")

    for blocked_id in expected.get("must_not_start", []) or []:
        if blocked_id == workflow_id:
            issues.append(f"must_not_start conflicts with workflow_id: {blocked_id}")

    for requirement in expected.get("required_text", []) or []:
        if not isinstance(requirement, dict):
            issues.append("required_text entry must be object")
            continue
        path_text = requirement.get("path")
        needle = requirement.get("contains")
        if not isinstance(path_text, str) or not isinstance(needle, str):
            issues.append("required_text requires path and contains")
            continue
        target = FACADE_ROOT / path_text
        if not target.is_file():
            issues.append(f"required_text path missing: {path_text}")
            continue
        if needle not in target.read_text(encoding="utf-8"):
            issues.append(f"required_text not found in {path_text}: {needle}")
    return issues


def load_cases() -> list[tuple[Path, dict[str, Any]]]:
    cases: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((SELF_IMPROVE_ROOT / "evals").glob("*.json")):
        if path.name == "schema.json":
            continue
        data = read_json(path)
        for case in data.get("cases", []):
            if isinstance(case, dict):
                cases.append((path, case))
    return cases


def load_changed_files(path_text: str | None) -> list[str]:
    if not path_text:
        return []
    data = read_json(Path(path_text))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("--changed-files must point to a JSON string array")
    return [item.replace("\\", "/") for item in data]


def changed_file_triggers(changed_files: list[str]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for changed in changed_files:
        for pattern in SELF_EVAL_TRIGGER_PATTERNS:
            if fnmatch.fnmatchcase(changed, pattern):
                hits.append({"path": changed, "pattern": pattern})
                break
    return hits


def validate_override_schema(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in data:
        if key not in ALLOWED_OVERRIDE_KEYS:
            issues.append(f"override key is not allowed by schema: {key}")

    additional_rules = data.get("additional_rules")
    if additional_rules is not None and (
        not isinstance(additional_rules, list) or not all(isinstance(item, str) for item in additional_rules)
    ):
        issues.append("additional_rules must be a string array")

    local_work_dirs = data.get("local_work_dirs")
    if local_work_dirs is not None:
        if not isinstance(local_work_dirs, dict):
            issues.append("local_work_dirs must be an object")
        else:
            for workflow_id, work_dir in local_work_dirs.items():
                if not isinstance(workflow_id, str) or not isinstance(work_dir, str):
                    issues.append("local_work_dirs keys and values must be strings")

    experimental_workflows = data.get("experimental_workflows")
    if experimental_workflows is not None:
        if not isinstance(experimental_workflows, list):
            issues.append("experimental_workflows must be an object array")
        else:
            for index, item in enumerate(experimental_workflows):
                if not isinstance(item, dict):
                    issues.append(f"experimental_workflows[{index}] must be object")
                    continue
                missing = sorted(REQUIRED_EXPERIMENTAL_WORKFLOW_KEYS - set(item))
                extra = sorted(set(item) - ALLOWED_EXPERIMENTAL_WORKFLOW_KEYS)
                if missing:
                    issues.append(f"experimental_workflows[{index}] missing keys: {missing}")
                if extra:
                    issues.append(f"experimental_workflows[{index}] has unsupported keys: {extra}")
                for value_key, value in item.items():
                    if value_key in ALLOWED_EXPERIMENTAL_WORKFLOW_KEYS and not isinstance(value, str):
                        issues.append(f"experimental_workflows[{index}].{value_key} must be string")
    return issues


def check_overrides() -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not LOCAL_OVERRIDES.exists():
        return findings
    for path in sorted(LOCAL_OVERRIDES.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(
                {
                    "path": path.relative_to(FACADE_ROOT).as_posix(),
                    "issue": "override file is not valid UTF-8",
                }
            )
            continue
        lowered = text.lower()
        for term in FORBIDDEN_OVERRIDE_TERMS:
            if term.lower() in lowered:
                findings.append(
                    {
                        "path": path.relative_to(FACADE_ROOT).as_posix(),
                        "issue": f"override contains forbidden term: {term}",
                    }
                )
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                findings.append(
                    {
                        "path": path.relative_to(FACADE_ROOT).as_posix(),
                        "issue": f"override JSON is invalid: {exc.msg}",
                    }
                )
                continue
            if not isinstance(data, dict):
                findings.append(
                    {
                        "path": path.relative_to(FACADE_ROOT).as_posix(),
                        "issue": "override JSON root must be object",
                    }
                )
                continue
            for issue in validate_override_schema(data):
                findings.append(
                    {
                        "path": path.relative_to(FACADE_ROOT).as_posix(),
                        "issue": issue,
                    }
                )
            if not OVERRIDE_SCHEMA.is_file():
                findings.append(
                    {
                        "path": "self-improve/overrides/schema.json",
                        "issue": "override schema missing",
                    }
                )
    return findings


def run_evals(changed_files: list[str] | None = None, *, include_overrides: bool = False) -> dict[str, Any]:
    registry = load_registry()
    static_issues = check_root_only_skill() + check_registry_paths(registry) + validate_manifest.validate_manifest()
    changed_files = changed_files or []
    trigger_hits = changed_file_triggers(changed_files)
    override_findings = check_overrides() if include_overrides else []
    results = []
    for path, case in load_cases():
        issues = validate_case(case, registry)
        results.append(
            {
                "file": path.relative_to(SELF_IMPROVE_ROOT).as_posix(),
                "id": case.get("id", "<missing>"),
                "category": case.get("category", "<missing>"),
                "passed": not issues,
                "issues": issues,
            }
        )
    passed = not static_issues and not override_findings and all(item["passed"] for item in results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "static_issues": static_issues,
        "changed_files": changed_files,
        "changed_file_triggers": trigger_hits,
        "override_findings": override_findings,
        "case_count": len(results),
        "case_results": results,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# lgwf-wf-agent Self Eval {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- case_count: `{report['case_count']}`",
        f"- static_issues: `{len(report['static_issues'])}`",
        f"- changed_file_triggers: `{len(report['changed_file_triggers'])}`",
        f"- override_findings: `{len(report['override_findings'])}`",
        "",
        "## Static Issues",
        "",
    ]
    if report["static_issues"]:
        lines.extend(f"- {issue}" for issue in report["static_issues"])
    else:
        lines.append("- none")
    lines.extend(["", "## Changed File Triggers", ""])
    if report["changed_file_triggers"]:
        lines.extend(f"- `{item['path']}` matched `{item['pattern']}`" for item in report["changed_file_triggers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Override Findings", ""])
    if report["override_findings"]:
        lines.extend(f"- `{item['path']}`: {item['issue']}" for item in report["override_findings"])
    else:
        lines.append("- none")
    lines.extend(["", "## Case Results", ""])
    for item in report["case_results"]:
        marker = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{marker}` `{item['id']}` ({item['category']})")
        for issue in item["issues"]:
            lines.append(f"  - {issue}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--changed-files", help="JSON file containing paths relative to facade root.")
    parser.add_argument("--check-overrides", action="store_true")
    args = parser.parse_args()

    report = run_evals(load_changed_files(args.changed_files), include_overrides=args.check_overrides)
    output_dir = Path(args.output_dir)
    base = output_dir / f"{utc_stamp()}-self-eval"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"passed": report["passed"], "json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
