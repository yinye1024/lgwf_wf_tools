from __future__ import annotations

from pathlib import Path
from typing import Any

from self_fix_common import read_json, read_text


def attempt_dir_from_target(target: dict[str, Any]) -> Path | None:
    raw = target.get("last_attempt_dir")
    if not raw and isinstance(target.get("last_attempt"), dict):
        raw = target["last_attempt"].get("work_dir")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    return path if path.exists() else None


def _stock_id(report: dict[str, Any]) -> str | None:
    for key in ("stock", "stock_id", "id", "name"):
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().replace(" ", "_")
    index = report.get("stock_index")
    if isinstance(index, int):
        return f"stock_{index}"
    return None


def _workflow_mentions(workflow_text: str, stock_id: str) -> bool:
    normalized = stock_id.replace(" ", "_")
    candidates = {
        normalized,
        normalized.replace("_", " "),
        f"analyze_{normalized}",
    }
    return any(candidate in workflow_text for candidate in candidates)


def _contract_path(attempt_dir: Path) -> Path | None:
    candidates = [
        attempt_dir / ".lgwf" / "workflow" / ".lgwf-contract.json",
        attempt_dir / ".lgwf-contract.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _required_file_entries(contract: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    raw = contract.get("required_files")
    if not isinstance(raw, list):
        return entries
    for item in raw:
        if isinstance(item, str):
            entries.append({"path": item, "required": True})
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            entries.append({"path": item["path"], "required": item.get("required", True)})
    return entries


def _scheduled_ids(workflow_text: str) -> list[str]:
    ids: set[str] = set()
    for index in range(1, 100):
        stock_id = f"stock_{index}"
        if _workflow_mentions(workflow_text, stock_id):
            ids.add(stock_id)
    return sorted(ids)


def _final_summary_reports(attempt_dir: Path) -> list[dict[str, Any]]:
    final_summary = read_json(attempt_dir / "reports" / "final_summary.json", {})
    if not isinstance(final_summary, dict):
        return []
    reports = final_summary.get("stock_reports")
    return reports if isinstance(reports, list) else []


def _collect_explicit_contract_audit(attempt_dir: Path, contract_file: Path) -> dict[str, Any]:
    contract = read_json(contract_file, {})
    if not isinstance(contract, dict):
        contract = {}
    issues: list[dict[str, Any]] = []
    required_files = _required_file_entries(contract)
    for entry in required_files:
        if entry.get("required") is False:
            continue
        relative_path = entry["path"]
        if (attempt_dir / relative_path).is_file():
            continue
        issues.append(
            {
                "phase": "output_contract",
                "error": f"required contract file is missing: {relative_path}",
                "work_dir": str(attempt_dir),
                "suggestion": "Repair the target workflow step or output writer that should create this required file.",
            }
        )
    return {
        "explicit_contract": True,
        "contract_path": str(contract_file),
        "required_files": required_files,
        "scheduled_ids": [],
        "final_summary_expected": [],
        "stale_expectations": [],
        "missing_outputs": [
            {"path": issue["error"].split(": ", 1)[1], "phase": issue["phase"]}
            for issue in issues
            if ": " in issue["error"]
        ],
        "issues": issues,
    }


def collect_contract_audit(attempt_dir: Path | None) -> dict[str, Any]:
    if attempt_dir is None:
        return {
            "explicit_contract": False,
            "scheduled_ids": [],
            "final_summary_expected": [],
            "stale_expectations": [],
            "missing_outputs": [],
            "issues": [],
        }
    contract_file = _contract_path(attempt_dir)
    if contract_file is not None:
        return _collect_explicit_contract_audit(attempt_dir, contract_file)
    reports = _final_summary_reports(attempt_dir)
    workflow_text = read_text(attempt_dir / ".lgwf" / "workflow" / "workflow.lgwf")
    scheduled = _scheduled_ids(workflow_text)
    expected: list[str] = []
    stale: list[dict[str, Any]] = []
    missing_outputs: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        stock_id = _stock_id(report)
        if not stock_id:
            continue
        expected.append(stock_id)
        missing = []
        if report.get("analysis_exists") is False:
            missing.append("analysis")
        if report.get("review_exists") is False:
            missing.append("review")
        if not missing:
            continue
        if workflow_text and not _workflow_mentions(workflow_text, stock_id):
            stale.append({"id": stock_id, "missing": missing})
            issues.append(
                {
                    "phase": "contract_drift",
                    "error": (
                        f"final_summary still expects {stock_id} {'/'.join(missing)}, "
                        "but the target root workflow does not schedule that stock."
                    ),
                    "work_dir": str(attempt_dir),
                    "suggestion": "Sync target finalize/verify/prompt contract with the current root workflow topology.",
                }
            )
        else:
            missing_outputs.append({"id": stock_id, "missing": missing})
            issues.append(
                {
                    "phase": "output_contract",
                    "error": f"scheduled target output is missing for {stock_id}: {', '.join(missing)}",
                    "work_dir": str(attempt_dir),
                    "suggestion": "Repair the scheduled target step or its output verification.",
                }
            )
    return {
        "explicit_contract": False,
        "scheduled_ids": scheduled,
        "final_summary_expected": sorted(set(expected)),
        "stale_expectations": stale,
        "missing_outputs": missing_outputs,
        "issues": issues,
    }


def collect_contract_issues(attempt_dir: Path | None) -> list[dict[str, Any]]:
    audit = collect_contract_audit(attempt_dir)
    issues = audit.get("issues")
    return issues if isinstance(issues, list) else []


def collect_run_health(attempt_dir: Path | None) -> dict[str, Any]:
    health: dict[str, Any] = {
        "warnings": [],
        "codex_stream_disconnects": 0,
        "codex_http_fallbacks": 0,
        "data_fallback": False,
    }
    if attempt_dir is None:
        return health
    data_dir = attempt_dir / "data"
    for path in (data_dir / "top_decliners.json", data_dir / "top_decliners.md"):
        text = read_text(path)
        if "fallback" in text.lower() or "latest_day_fallback" in text:
            health["data_fallback"] = True
            health["warnings"].append({"type": "data_fallback", "path": str(path)})
            break
    codex_dir = attempt_dir / ".lgwf" / "codex"
    if codex_dir.exists():
        for stderr in codex_dir.rglob("stderr.txt"):
            text = read_text(stderr)
            disconnects = text.count("stream disconnected")
            fallbacks = text.count("falling back to HTTP")
            if disconnects:
                health["codex_stream_disconnects"] += disconnects
            if fallbacks:
                health["codex_http_fallbacks"] += fallbacks
    if health["codex_stream_disconnects"]:
        health["warnings"].append({"type": "codex_stream_disconnect", "count": health["codex_stream_disconnects"]})
    if health["codex_http_fallbacks"]:
        health["warnings"].append({"type": "codex_http_fallback", "count": health["codex_http_fallbacks"]})
    return health


def has_repairable_contract_issue(issues: list[dict[str, Any]]) -> bool:
    return any(issue.get("phase") in {"contract_drift", "output_contract"} for issue in issues)


def compress_history(history: list[Any]) -> list[Any]:
    compressed: list[Any] = []
    for item in history:
        if not isinstance(item, dict):
            compressed.append(item)
            continue
        normalized = dict(item)
        if item.get("event") == "target_still_running" or (
            item.get("event") == "route_after_observe"
            and item.get("route") == "observe"
            and item.get("status") == "running"
        ):
            normalized = {
                "event": "target_running_poll",
                "status": "running",
                **{key: value for key, value in item.items() if key in {"ts", "timestamp", "time"}},
            }
        comparable = {key: value for key, value in normalized.items() if key not in {"ts", "timestamp", "time"}}
        if compressed and isinstance(compressed[-1], dict):
            previous = compressed[-1]
            previous_comparable = {
                key: value
                for key, value in previous.items()
                if key not in {"ts", "timestamp", "time", "first_ts", "last_ts", "count"}
            }
            if previous_comparable == comparable:
                previous["count"] = int(previous.get("count", 1)) + 1
                previous["last_ts"] = item.get("ts") or item.get("timestamp") or item.get("time")
                previous.setdefault("first_ts", previous.get("ts"))
                previous.pop("ts", None)
                continue
        compressed.append(normalized)
    return compressed
