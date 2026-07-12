from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lgwf_wf_create_real_positive_e2e import (
    FACADE_ROOT,
    REPORT_RELATIVE,
    TARGET_PACKAGE_ROOT,
    TARGET_STAGE_DIRS,
    WORKFLOW_LGWF,
    WORKFLOW_NAME,
    allows_simple_approve,
    contains_text,
    kill_process_tree,
    parse_json_text,
    prepare_temp_workspace,
    read_json,
    real_positive_fixture,
    request_id_from_item,
    request_payload,
    run_completed,
    sanitize_request_id,
    status_indicates_waiting_human,
    write_json,
    write_text,
)


WF_FIX_ENTRY = "skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf"
WF_FIX_LGWF = FACADE_ROOT / "workflows" / "wf-fix" / "wf" / "workflow.lgwf"
WF_FIX_FAILURE_SUMMARY_NAME = "wf_fix_failure_summary.json"
SELF_FIX_MAX_ATTEMPTS = 5
ASK_MAIN_AGENT_FOR_TARGET_APPROVALS = True
WF_FIX_APPROVAL_COMMENT = "wf-fix positive e2e auto approve"
WF_FIX_INITIAL_RUN_TIMEOUT_SECONDS = 900
WF_FIX_POST_APPROVAL_TIMEOUT_SECONDS = 180


def target_workflow_input_submission(fixture_path: Path) -> dict[str, Any]:
    fixture = real_positive_fixture()
    return {
        "input_json_file": fixture_path.as_posix(),
        "input_json": fixture,
        "raw_intent": str(fixture.get("raw_intent", "")).strip(),
    }


def build_wf_fix_input_payload(fixture_path: Path) -> dict[str, Any]:
    submission = target_workflow_input_submission(fixture_path)
    self_fix_request = {
        "target_workflow_lgwf": str(WORKFLOW_LGWF),
        "target_workflow_input": submission,
        "max_attempts": SELF_FIX_MAX_ATTEMPTS,
        "ask_main_agent_for_target_approvals": ASK_MAIN_AGENT_FOR_TARGET_APPROVALS,
    }
    payload = dict(self_fix_request)
    payload["self_fix_request"] = dict(self_fix_request)
    payload["target_workflow_input_json_file"] = fixture_path.as_posix()
    payload["target_workflow_input_file"] = fixture_path.as_posix()
    return payload


def json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(item) for item in value]
    return value


def build_failure_summary_base(
    *,
    temp_root: Path,
    work_dir: Path,
    artifacts_dir: Path,
    fixture_path: Path,
    wf_fix_input_path: Path,
    output_json_path: Path,
) -> dict[str, Any]:
    return {
        "status": "initial_placeholder",
        "phase": "bootstrap_before_audit",
        "wf_fix_entry": WF_FIX_ENTRY,
        "target_workflow_lgwf": str(WORKFLOW_LGWF),
        "self_fix_request": {
            "target_workflow_lgwf": str(WORKFLOW_LGWF),
            "max_attempts": SELF_FIX_MAX_ATTEMPTS,
            "ask_main_agent_for_target_approvals": ASK_MAIN_AGENT_FOR_TARGET_APPROVALS,
        },
        "temp_workspace": temp_root,
        "work_dir": work_dir,
        "artifacts_dir": artifacts_dir,
        "fixture_path": fixture_path,
        "wf_fix_input_path": wf_fix_input_path,
        "output_json_path": output_json_path,
        "retained_paths": [
            artifacts_dir / "target_workflow_audit.stdout.txt",
            artifacts_dir / "target_workflow_audit.stderr.txt",
            artifacts_dir / "wf_fix_run.stdout.txt",
            artifacts_dir / "wf_fix_run.stderr.txt",
            artifacts_dir / WF_FIX_FAILURE_SUMMARY_NAME,
            fixture_path,
            wf_fix_input_path,
            work_dir,
            work_dir / ".lgwf",
            temp_root / TARGET_PACKAGE_ROOT,
        ],
    }


def write_failure_summary(
    summary_path: Path,
    base_summary: dict[str, Any],
    *,
    status: str,
    phase: str,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> None:
    summary = dict(base_summary)
    summary["status"] = status
    summary["phase"] = phase
    summary["reason"] = reason
    if extra:
        summary.update(extra)
    write_json(summary_path, json_ready(summary))


def capture_workflow_status(
    lgwf_py: Path,
    *,
    work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
    prefix: str,
    label: str,
) -> tuple[subprocess.CompletedProcess[str], Any | None]:
    stdout_path = artifacts_dir / f"{prefix}_status_{label}.stdout.txt"
    stderr_path = artifacts_dir / f"{prefix}_status_{label}.stderr.txt"
    completed = run_completed(
        [sys.executable, str(lgwf_py), "status", "--work-dir", str(work_dir)],
        cwd=temp_root,
        env=env,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout_seconds=120,
    )
    return completed, parse_json_text(completed.stdout)


def request_text_lower(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False).lower()
    except TypeError:
        return str(payload).lower()


def request_requires_value_json(payload: Any) -> bool:
    request = request_payload(payload)
    for key in (
        "requires_value_json",
        "needs_value_json",
        "value_required",
        "requires_value",
    ):
        if request.get(key) is True:
            return True
    return bool(request.get("value_json_schema") or request.get("value_schema"))


def schema_type(schema: Any) -> str:
    if not isinstance(schema, dict):
        return ""
    raw = schema.get("type")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        for item in raw:
            if str(item) != "null":
                return str(item)
    return ""


def iter_schema_variants(schema: Any) -> list[dict[str, Any]]:
    if not isinstance(schema, dict):
        return []
    variants = [schema]
    for key in ("oneOf", "anyOf", "allOf"):
        value = schema.get(key)
        if isinstance(value, list):
            variants.extend(item for item in value if isinstance(item, dict))
    return variants


def looks_like_target_input_request(payload: Any) -> bool:
    text = request_text_lower(payload)
    return any(
        token in text
        for token in (
            "collect_target_workflow_input",
            "target_workflow_input",
            "target workflow input",
            "input_json",
            "raw_intent",
        )
    )


def looks_like_target_input_schema(schema: Any) -> bool:
    return any(
        token in request_text_lower(schema)
        for token in (
            "target_workflow_input",
            "input_json",
            "raw_intent",
            "target_workflow_lgwf",
        )
    )


def build_property_value(name: str, prop_schema: Any, fixture_path: Path) -> Any | None:
    lower = name.lower()
    kind = schema_type(prop_schema)
    fixture = real_positive_fixture()

    if "target_workflow_lgwf" in lower:
        return str(WORKFLOW_LGWF)
    if "max_attempt" in lower:
        return SELF_FIX_MAX_ATTEMPTS
    if "ask_main_agent_for_target_approval" in lower:
        return ASK_MAIN_AGENT_FOR_TARGET_APPROVALS
    if lower == "raw_intent" or lower.endswith("_raw_intent"):
        return str(fixture.get("raw_intent", "")).strip()
    if "target_workflow_input" in lower or lower.endswith("workflow_input"):
        if kind == "string":
            return fixture_path.as_posix()
        return target_workflow_input_submission(fixture_path)
    if "input_json_file" in lower or lower.endswith("_json_file") or lower.endswith("_file") or "fixture" in lower:
        return fixture_path.as_posix()
    if lower == "input_json" or lower.endswith("_input_json"):
        if kind == "string":
            return json.dumps(fixture, ensure_ascii=False)
        return fixture
    if lower.endswith("_json"):
        if kind == "string":
            return json.dumps(fixture, ensure_ascii=False)
        return fixture
    if "workflow" in lower and kind == "string":
        return str(WORKFLOW_LGWF)
    if any(token in lower for token in ("request", "payload", "submission", "value")):
        nested = build_value_for_schema(prop_schema, fixture_path)
        if nested is not None:
            return nested
    return None


def build_value_for_schema(schema: Any, fixture_path: Path) -> Any | None:
    for variant in iter_schema_variants(schema):
        kind = schema_type(variant)
        properties = variant.get("properties") if isinstance(variant, dict) else None
        if kind == "object" or isinstance(properties, dict):
            if isinstance(properties, dict) and properties:
                result: dict[str, Any] = {}
                for name, prop_schema in properties.items():
                    value = build_property_value(name, prop_schema, fixture_path)
                    if value is not None:
                        result[name] = value
                if result or not variant.get("required"):
                    return result
            if looks_like_target_input_schema(variant):
                return target_workflow_input_submission(fixture_path)
        if kind == "string":
            return fixture_path.as_posix()
        if kind == "boolean":
            return True
        if kind == "integer":
            return SELF_FIX_MAX_ATTEMPTS
        if kind == "number":
            return float(SELF_FIX_MAX_ATTEMPTS)
        if kind == "array":
            item_value = build_value_for_schema(variant.get("items"), fixture_path)
            if item_value is None:
                return []
            return [item_value]
    if looks_like_target_input_schema(schema):
        return target_workflow_input_submission(fixture_path)
    return None


def build_value_json_for_request(payload: Any, fixture_path: Path) -> Any:
    request = request_payload(payload)
    schema = request.get("value_json_schema") or request.get("value_schema")
    built = build_value_for_schema(schema, fixture_path)
    if built is not None:
        return built
    if looks_like_target_input_request(payload):
        return target_workflow_input_submission(fixture_path)
    return build_wf_fix_input_payload(fixture_path)


def approval_submit_args(
    lgwf_py: Path,
    *,
    work_dir: Path,
    request_id: str,
    value_json: Any | None,
) -> list[str]:
    args = [
        sys.executable,
        str(lgwf_py),
        "approval",
        "submit",
        "--work-dir",
        str(work_dir),
        "--request-id",
        request_id,
        "--decision",
        "approve",
    ]
    if value_json is not None:
        args.extend(["--value-json", json.dumps(value_json, ensure_ascii=False)])
    args.extend(["--comment", WF_FIX_APPROVAL_COMMENT])
    return args


def collect_pending_approvals_for_work_dir(
    lgwf_py: Path,
    *,
    work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
    fixture_path: Path,
    label: str,
    submitted_request_ids: set[str],
    auto_submit: bool,
) -> dict[str, Any]:
    # wf-fix 与 target run 的自动 approval 固定走 approval list -> approval get -> approval submit。
    list_completed = run_completed(
        [sys.executable, str(lgwf_py), "approval", "list", "--work-dir", str(work_dir)],
        cwd=temp_root,
        env=env,
        stdout_path=artifacts_dir / f"{label}_approval_list.stdout.txt",
        stderr_path=artifacts_dir / f"{label}_approval_list.stderr.txt",
        timeout_seconds=120,
    )
    parsed_list = parse_json_text(list_completed.stdout)
    requests = []
    if isinstance(parsed_list, dict) and isinstance(parsed_list.get("requests"), list):
        requests = parsed_list["requests"]

    request_ids: list[str] = []
    attempted_request_ids: list[str] = []
    request_payload_paths: list[str] = []

    for item in requests:
        request_id = request_id_from_item(item)
        if not request_id:
            continue
        request_ids.append(request_id)
        safe_id = sanitize_request_id(request_id)
        get_completed = run_completed(
            [
                sys.executable,
                str(lgwf_py),
                "approval",
                "get",
                "--work-dir",
                str(work_dir),
                "--request-id",
                request_id,
            ],
            cwd=temp_root,
            env=env,
            stdout_path=artifacts_dir / f"{label}_approval_{safe_id}.stdout.txt",
            stderr_path=artifacts_dir / f"{label}_approval_{safe_id}.stderr.txt",
            timeout_seconds=120,
        )
        payload_path = artifacts_dir / f"{label}_approval_{safe_id}.json"
        write_text(payload_path, get_completed.stdout)
        request_payload_paths.append(str(payload_path))
        payload = parse_json_text(get_completed.stdout)

        if not auto_submit or request_id in submitted_request_ids:
            continue

        submit_args: list[str] | None = None
        if allows_simple_approve(payload, request_id):
            submit_args = approval_submit_args(
                lgwf_py,
                work_dir=work_dir,
                request_id=request_id,
                value_json=None,
            )
        elif looks_like_target_input_request(payload):
            submit_args = approval_submit_args(
                lgwf_py,
                work_dir=work_dir,
                request_id=request_id,
                value_json=build_value_json_for_request(payload, fixture_path),
            )

        if submit_args is None:
            continue

        submit_completed = run_completed(
            submit_args,
            cwd=temp_root,
            env=env,
            stdout_path=artifacts_dir / f"{label}_approval_{safe_id}.submit.stdout.txt",
            stderr_path=artifacts_dir / f"{label}_approval_{safe_id}.submit.stderr.txt",
            timeout_seconds=120,
        )
        if submit_completed.returncode == 0:
            submitted_request_ids.add(request_id)
            attempted_request_ids.append(request_id)

    return {
        "label": label,
        "work_dir": str(work_dir),
        "request_ids": request_ids,
        "attempted_request_ids": attempted_request_ids,
        "request_payload_paths": request_payload_paths,
    }


def iter_target_run_work_dirs(temp_root: Path) -> list[Path]:
    candidates: list[tuple[float, Path]] = []
    for work_dir in temp_root.rglob("work"):
        if not work_dir.is_dir() or not (work_dir / ".lgwf").is_dir():
            continue
        parts = [part.lower() for part in work_dir.parts]
        if "target_runs" not in parts:
            continue
        if not any(part.lower().startswith("attempt-") for part in work_dir.parts):
            continue
        candidates.append(((work_dir / ".lgwf").stat().st_mtime, work_dir))
    seen: set[str] = set()
    ordered: list[Path] = []
    for _, work_dir in sorted(candidates, key=lambda item: item[0], reverse=True):
        key = str(work_dir)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(work_dir)
    return ordered


def target_run_contexts(temp_root: Path) -> list[dict[str, Path]]:
    contexts: list[dict[str, Path]] = []
    seen: set[str] = set()

    def add_context(work_dir: Path) -> None:
        workspace_root = work_dir.parent
        target_root = workspace_root / TARGET_PACKAGE_ROOT
        summary_path = work_dir / ".lgwf" / "create_result_summary.json"
        target_workflow = target_root / "wf" / "workflow.lgwf"
        if not summary_path.is_file() and not target_workflow.is_file():
            return
        key = str(work_dir)
        if key in seen:
            return
        seen.add(key)
        contexts.append(
            {
                "workspace_root": workspace_root,
                "work_dir": work_dir,
                "target_root": target_root,
                "summary_path": summary_path,
                "target_workflow": target_workflow,
            }
        )

    for work_dir in iter_target_run_work_dirs(temp_root):
        add_context(work_dir)

    for workflow_path in temp_root.rglob("skills/runtime-e2e-created/wf/workflow.lgwf"):
        workspace_root = workflow_path.parents[3]
        add_context(workspace_root / "work")

    def score(item: dict[str, Path]) -> float:
        summary_path = item["summary_path"]
        target_workflow = item["target_workflow"]
        if summary_path.is_file():
            return summary_path.stat().st_mtime
        return target_workflow.stat().st_mtime

    return sorted(contexts, key=score, reverse=True)


def latest_target_run_context(temp_root: Path) -> dict[str, Path] | None:
    contexts = target_run_contexts(temp_root)
    return contexts[0] if contexts else None


def collect_all_pending_approvals(
    lgwf_py: Path,
    *,
    wf_fix_work_dir: Path,
    temp_root: Path,
    artifacts_dir: Path,
    env: dict[str, str],
    fixture_path: Path,
    submitted_request_ids: set[str],
    auto_submit: bool,
) -> list[dict[str, Any]]:
    work_dirs = [wf_fix_work_dir, *iter_target_run_work_dirs(temp_root)]
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for work_dir in work_dirs:
        key = str(work_dir)
        if key in seen:
            continue
        seen.add(key)
        if work_dir == wf_fix_work_dir:
            label = "wf_fix"
        else:
            relative = work_dir.relative_to(temp_root).as_posix()
            label = f"target_{sanitize_request_id(relative)}"
        results.append(
            collect_pending_approvals_for_work_dir(
                lgwf_py,
                work_dir=work_dir,
                temp_root=temp_root,
                artifacts_dir=artifacts_dir,
                env=env,
                fixture_path=fixture_path,
                label=label,
                submitted_request_ids=submitted_request_ids,
                auto_submit=auto_submit,
            )
        )
    return results


def aggregate_request_ids(results: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for item in results:
        raw = item.get(key, [])
        if isinstance(raw, list):
            values.extend(str(entry) for entry in raw if str(entry).strip())
    return values


def aggregate_payload_paths(results: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for item in results:
        raw = item.get("request_payload_paths", [])
        if isinstance(raw, list):
            values.extend(str(entry) for entry in raw if str(entry).strip())
    return values


def extract_named_object(payload: Any, tokens: tuple[str, ...]) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lower = key.lower()
            if all(token in lower for token in tokens) and isinstance(value, dict):
                return value
            found = extract_named_object(value, tokens)
            if found is not None:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = extract_named_object(item, tokens)
            if found is not None:
                return found
    return None


def load_latest_self_fix_summary(
    temp_root: Path,
    wf_fix_work_dir: Path,
    output_json_path: Path,
) -> tuple[Path | None, dict[str, Any] | None]:
    candidates: list[tuple[float, Path, dict[str, Any]]] = []
    files: list[Path] = []
    if output_json_path.is_file():
        files.append(output_json_path)
    files.extend(wf_fix_work_dir.rglob("*self_fix*summary*.json"))
    files.extend(temp_root.rglob("*self_fix*summary*.json"))

    seen: set[str] = set()
    for path in files:
        key = str(path)
        if key in seen or not path.is_file():
            continue
        seen.add(key)
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        if "self_fix_summary" in path.name.lower():
            summary = data
        else:
            summary = extract_named_object(data, ("self", "fix", "summary"))
        if isinstance(summary, dict):
            candidates.append((path.stat().st_mtime, path, summary))

    if not candidates:
        return None, None
    _, path, summary = sorted(candidates, key=lambda item: item[0], reverse=True)[0]
    return path, summary


def collect_status_like_strings(payload: Any) -> list[str]:
    values: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lower = key.lower()
            if isinstance(value, (str, int, float, bool)) and any(
                token in lower for token in ("status", "result", "outcome", "decision", "summary")
            ):
                values.append(str(value).lower())
            values.extend(collect_status_like_strings(value))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(collect_status_like_strings(item))
    return values


def self_fix_summary_indicates_success(summary: dict[str, Any]) -> bool:
    joined = " ".join(collect_status_like_strings(summary))
    if "fixed" in joined or "succeeded" in joined:
        return True
    return contains_text(summary, "fixed") or contains_text(summary, "succeeded")


def self_fix_summary_has_blockers(summary: dict[str, Any]) -> bool:
    raw = json.dumps(summary, ensure_ascii=False)
    if status_indicates_waiting_human(summary, raw):
        return True
    if contains_text(summary, "timeout"):
        return True
    if contains_text(summary, "unresolved") and contains_text(summary, "approval"):
        return True
    return False


class LgwfWfCreateRealPositiveForWfFixE2ETest(unittest.TestCase):
    maxDiff = None

    def assert_target_run_business_outcome(
        self,
        *,
        target_context: dict[str, Path],
        artifacts_dir: Path,
        env: dict[str, str],
    ) -> None:
        workspace_root = target_context["workspace_root"]
        work_dir = target_context["work_dir"]
        target_root = target_context["target_root"]
        summary_path = target_context["summary_path"]
        target_vendor_lgwf = workspace_root / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"

        self.assertTrue(target_root.is_dir(), f"target package missing after wf-fix: {target_root}")
        self.assertFalse((target_root / ".lgwf").exists(), f"target package leaked runtime state: {target_root / '.lgwf'}")
        self.assertTrue(target_vendor_lgwf.is_file(), f"target run missing mirrored vendor runtime: {target_vendor_lgwf}")

        for relative_path in ("AGENTS.md", "README.md", "entry_contract.json", "wf/workflow.lgwf"):
            file_path = target_root / relative_path
            with self.subTest(file=relative_path):
                self.assertTrue(file_path.is_file(), f"missing file: {file_path}")
                file_path.read_text(encoding="utf-8")

        for stage_dir in TARGET_STAGE_DIRS:
            stage_root = target_root / "wf" / stage_dir
            with self.subTest(stage=stage_dir):
                self.assertTrue((stage_root / "workflow.lgwf").is_file(), stage_root)
                self.assertTrue((stage_root / "agents").is_dir(), stage_root)
                self.assertTrue((stage_root / "scripts").is_dir(), stage_root)
                self.assertTrue((stage_root / "resources").is_dir(), stage_root)

        for relative_path in (
            "wf/docs/steps/collect-context.md",
            "wf/docs/steps/run-checks.md",
            "tests/test_workflow_structure.py",
        ):
            self.assertTrue((target_root / relative_path).is_file(), f"missing generated artifact: {relative_path}")

        created_package_audit = run_completed(
            [sys.executable, str(target_vendor_lgwf), "audit", str(target_root / "wf" / "workflow.lgwf")],
            cwd=workspace_root,
            env=env,
            stdout_path=artifacts_dir / "generated_package_after_wf_fix_audit.stdout.txt",
            stderr_path=artifacts_dir / "generated_package_after_wf_fix_audit.stderr.txt",
            timeout_seconds=240,
        )
        self.assertEqual(
            created_package_audit.returncode,
            0,
            "\n".join(
                [
                    "wf-fix 后最后一轮 target run 生成的 package 未通过 authoring audit。",
                    f"workspace_root={workspace_root}",
                    f"stdout={artifacts_dir / 'generated_package_after_wf_fix_audit.stdout.txt'}",
                    f"stderr={artifacts_dir / 'generated_package_after_wf_fix_audit.stderr.txt'}",
                ]
            ),
        )

        package_unittest = run_completed(
            [sys.executable, "-m", "unittest", "discover", "tests"],
            cwd=target_root,
            env=env,
            stdout_path=artifacts_dir / "generated_package_after_wf_fix_unittest.stdout.txt",
            stderr_path=artifacts_dir / "generated_package_after_wf_fix_unittest.stderr.txt",
            timeout_seconds=240,
        )
        self.assertEqual(
            package_unittest.returncode,
            0,
            "\n".join(
                [
                    "wf-fix 后最后一轮 target run 生成的 package 最小 unittest 未通过。",
                    f"workspace_root={workspace_root}",
                    f"stdout={artifacts_dir / 'generated_package_after_wf_fix_unittest.stdout.txt'}",
                    f"stderr={artifacts_dir / 'generated_package_after_wf_fix_unittest.stderr.txt'}",
                ]
            ),
        )

        self.assertTrue(summary_path.is_file(), f"missing last target run summary: {summary_path}")
        summary = read_json(summary_path)
        self.assertEqual(
            summary.get("status"),
            "draft_structure_ready",
            f"unexpected last target run status: {summary_path}",
        )
        self.assertEqual(
            str(summary.get("report_path", "")).replace("\\", "/"),
            REPORT_RELATIVE.as_posix(),
            f"unexpected report path in summary: {summary_path}",
        )

        report_path = work_dir / REPORT_RELATIVE
        self.assertTrue(report_path.is_file(), f"missing report after wf-fix target run: {report_path}")
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn(WORKFLOW_NAME, report_text)
        self.assertIn(TARGET_PACKAGE_ROOT, report_text)
        self.assertIn("python -m unittest discover tests", report_text)

    def test_real_positive_minimal_runtime_e2e_created_flow_via_wf_fix(self) -> None:
        self.assertTrue(WORKFLOW_LGWF.is_file(), f"workflow missing: {WORKFLOW_LGWF}")
        self.assertTrue(WF_FIX_LGWF.is_file(), f"wf-fix workflow missing: {WF_FIX_LGWF}")
        self.assertIsNotNone(shutil.which("codex"), "PATH 中缺少 codex，无法运行 wf-fix 正向 E2E。")

        temp_root = Path(tempfile.mkdtemp(prefix="lgwf-wf-create-wf-fix-"))
        success = False
        current_phase = "bootstrap"
        submitted_request_ids: set[str] = set()
        timed_out_before_approval = False
        failure_summary_path: Path | None = None
        failure_summary_base: dict[str, Any] = {}
        failure_context: dict[str, Any] = {}
        try:
            prepared = prepare_temp_workspace(temp_root)
            work_dir = prepared["work_dir"]
            artifacts_dir = prepared["artifacts_dir"]
            fixtures_dir = prepared["fixtures_dir"]
            lgwf_py = prepared["lgwf_py"]

            fixture_path = fixtures_dir / "real_positive_create_request.json"
            wf_fix_input_path = fixtures_dir / "wf_fix_target_request.json"
            output_json_path = artifacts_dir / "wf_fix_output.json"
            wf_fix_stdout_path = artifacts_dir / "wf_fix_run.stdout.txt"
            wf_fix_stderr_path = artifacts_dir / "wf_fix_run.stderr.txt"
            failure_summary_path = artifacts_dir / WF_FIX_FAILURE_SUMMARY_NAME

            write_json(fixture_path, real_positive_fixture())
            write_json(wf_fix_input_path, build_wf_fix_input_payload(fixture_path))
            write_text(wf_fix_stdout_path, "")
            write_text(wf_fix_stderr_path, "")
            failure_summary_base = build_failure_summary_base(
                temp_root=temp_root,
                work_dir=work_dir,
                artifacts_dir=artifacts_dir,
                fixture_path=fixture_path,
                wf_fix_input_path=wf_fix_input_path,
                output_json_path=output_json_path,
            )
            write_failure_summary(
                failure_summary_path,
                failure_summary_base,
                status="initial_placeholder",
                phase="bootstrap_before_audit",
                reason="wf-fix positive e2e initialized",
            )
            self.assertFalse((temp_root / TARGET_PACKAGE_ROOT).exists(), "target package should start absent before wf-fix")

            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            failure_context = {
                "submitted_request_ids": [],
                "timed_out_before_approval": timed_out_before_approval,
            }

            # 启动 wf-fix 前必须先执行 lgwf.py audit <target workflow.lgwf>。
            current_phase = "pre_run_audit"
            audit_completed = run_completed(
                [sys.executable, str(lgwf_py), "audit", str(WORKFLOW_LGWF)],
                cwd=temp_root,
                env=env,
                stdout_path=artifacts_dir / "target_workflow_audit.stdout.txt",
                stderr_path=artifacts_dir / "target_workflow_audit.stderr.txt",
                timeout_seconds=240,
            )
            failure_context["audit_exit_code"] = audit_completed.returncode
            if audit_completed.returncode != 0:
                self.fail(
                    "\n".join(
                        [
                            "原始目标 workflow audit 未通过，wf-fix 正向入口已终止。",
                            f"temp_workspace={temp_root}",
                            f"stdout={artifacts_dir / 'target_workflow_audit.stdout.txt'}",
                            f"stderr={artifacts_dir / 'target_workflow_audit.stderr.txt'}",
                        ]
                    )
                )

            run_args = [
                sys.executable,
                str(lgwf_py),
                "run",
                "--workflow-lgwf",
                str(WF_FIX_LGWF),
                "--work-dir",
                str(work_dir),
                "--input-json-file",
                str(wf_fix_input_path),
                "--auto-human",
                "--rerun-existing",
                "--output-json",
                str(output_json_path),
            ]

            stdout_handle = wf_fix_stdout_path.open("w", encoding="utf-8")
            stderr_handle = wf_fix_stderr_path.open("w", encoding="utf-8")
            try:
                current_phase = "wf_fix_run"
                process = subprocess.Popen(
                    run_args,
                    cwd=str(temp_root),
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                )
                returncode: int | None = None
                try:
                    returncode = process.wait(timeout=WF_FIX_INITIAL_RUN_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    timed_out_before_approval = True
                    failure_context["timed_out_before_approval"] = True
                    capture_workflow_status(
                        lgwf_py,
                        work_dir=work_dir,
                        temp_root=temp_root,
                        artifacts_dir=artifacts_dir,
                        env=env,
                        prefix="wf_fix",
                        label="timeout_before_approval",
                    )
                    approval_results = collect_all_pending_approvals(
                        lgwf_py,
                        wf_fix_work_dir=work_dir,
                        temp_root=temp_root,
                        artifacts_dir=artifacts_dir,
                        env=env,
                        fixture_path=fixture_path,
                        submitted_request_ids=submitted_request_ids,
                        auto_submit=True,
                    )
                    failure_context["submitted_request_ids"] = sorted(submitted_request_ids)
                    failure_context["approval_results"] = approval_results
                    try:
                        returncode = process.wait(timeout=WF_FIX_POST_APPROVAL_TIMEOUT_SECONDS)
                    except subprocess.TimeoutExpired:
                        current_phase = "waiting_human_after_auto_approval"
                        kill_process_tree(process)
                        self.fail(
                            "\n".join(
                                [
                                    "wf-fix 运行在自动 approval 后仍未进入终态。",
                                    f"temp_workspace={temp_root}",
                                    f"work_dir={work_dir}",
                                    f"retained_artifacts={artifacts_dir}",
                                    f"pending_request_ids={aggregate_request_ids(approval_results, 'request_ids')}",
                                    f"auto_approved_request_ids={aggregate_request_ids(approval_results, 'attempted_request_ids')}",
                                    f"pending_request_payloads={aggregate_payload_paths(approval_results)}",
                                ]
                            )
                        )
                failure_context["returncode"] = returncode
                current_phase = "final_status_check"
                final_status_completed, final_status_payload = capture_workflow_status(
                    lgwf_py,
                    work_dir=work_dir,
                    temp_root=temp_root,
                    artifacts_dir=artifacts_dir,
                    env=env,
                    prefix="wf_fix",
                    label="final",
                )
                failure_context["final_status_stdout_path"] = artifacts_dir / "wf_fix_status_final.stdout.txt"
                failure_context["final_status_stderr_path"] = artifacts_dir / "wf_fix_status_final.stderr.txt"
            finally:
                stdout_handle.close()
                stderr_handle.close()

            if returncode != 0 or status_indicates_waiting_human(final_status_payload, final_status_completed.stdout):
                current_phase = "wf_fix_failure"
                final_approvals = collect_all_pending_approvals(
                    lgwf_py,
                    wf_fix_work_dir=work_dir,
                    temp_root=temp_root,
                    artifacts_dir=artifacts_dir,
                    env=env,
                    fixture_path=fixture_path,
                    submitted_request_ids=submitted_request_ids,
                    auto_submit=False,
                )
                failure_context["submitted_request_ids"] = sorted(submitted_request_ids)
                failure_context["final_approvals"] = final_approvals
                self.fail(
                    "\n".join(
                        [
                            "wf-fix 正向运行未成功完成，或仍停留在 waiting_human。",
                            f"returncode={returncode}",
                            f"timed_out_before_approval={timed_out_before_approval}",
                            f"temp_workspace={temp_root}",
                            f"work_dir={work_dir}",
                            f"retained_artifacts={artifacts_dir}",
                            f"pending_request_ids={aggregate_request_ids(final_approvals, 'request_ids')}",
                            f"pending_request_payloads={aggregate_payload_paths(final_approvals)}",
                        ]
                    )
                )

            current_phase = "wf_fix_output_validation"
            if not output_json_path.is_file():
                self.fail(f"missing wf-fix output json: {output_json_path}")

            current_phase = "self_fix_summary_validation"
            self_fix_summary_path, self_fix_summary = load_latest_self_fix_summary(temp_root, work_dir, output_json_path)
            failure_context["self_fix_summary_path"] = self_fix_summary_path
            failure_context["self_fix_summary"] = self_fix_summary
            if self_fix_summary_path is None:
                self.fail(f"missing self_fix_summary under {temp_root}")
            if not isinstance(self_fix_summary, dict):
                self.fail(f"self_fix_summary is not a json object: {self_fix_summary_path}")
            if not self_fix_summary_indicates_success(self_fix_summary):
                self.fail(f"self_fix_summary does not report fixed/succeeded: {self_fix_summary_path}")
            if self_fix_summary_has_blockers(self_fix_summary):
                self.fail(f"self_fix_summary still contains unresolved approval or timeout: {self_fix_summary_path}")

            current_phase = "target_run_discovery"
            target_context = latest_target_run_context(temp_root)
            failure_context["target_context"] = target_context
            if target_context is None:
                self.fail(
                    "\n".join(
                        [
                            "wf-fix 结束后未发现最后一轮 target run 的业务结果工作区。",
                            f"temp_workspace={temp_root}",
                            f"work_dir={work_dir}",
                            f"self_fix_summary={self_fix_summary_path}",
                        ]
                    )
                )

            current_phase = "final_business_assertions"
            self.assert_target_run_business_outcome(
                target_context=target_context,
                artifacts_dir=artifacts_dir,
                env=env,
            )

            success = True
        except AssertionError as exc:
            if failure_summary_path is not None:
                failure_context["submitted_request_ids"] = sorted(submitted_request_ids)
                failure_context["timed_out_before_approval"] = timed_out_before_approval
                status = "audit_failure" if current_phase == "pre_run_audit" else "wf_fix_failure"
                if current_phase == "waiting_human_after_auto_approval":
                    status = "waiting_human_after_auto_approval"
                write_failure_summary(
                    failure_summary_path,
                    failure_summary_base,
                    status=status,
                    phase=current_phase,
                    reason=str(exc) or exc.__class__.__name__,
                    extra=failure_context,
                )
            raise
        except Exception as exc:
            if failure_summary_path is not None:
                failure_context["submitted_request_ids"] = sorted(submitted_request_ids)
                failure_context["timed_out_before_approval"] = timed_out_before_approval
                write_failure_summary(
                    failure_summary_path,
                    failure_summary_base,
                    status="unexpected_error",
                    phase=current_phase,
                    reason=f"{type(exc).__name__}: {exc}",
                    extra=failure_context,
                )
            raise
        finally:
            if success:
                shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
