import contextlib
import contextvars
from typing import Any


RunMetrics = dict[str, Any]

_BENIGN_STDERR_PATTERNS = (
    "Reading additional input from stdin...",
)
_BENIGN_STDERR_PREFIXES = (
    "OpenAI Codex ",
)

_CURRENT_METRICS: contextvars.ContextVar[list[RunMetrics] | None] = contextvars.ContextVar(
    "lgwf_run_metrics",
    default=None,
)


@contextlib.contextmanager
def collect_run_metrics(enabled: bool):
    metrics: list[RunMetrics] | None = [] if enabled else None
    token = _CURRENT_METRICS.set(metrics)
    try:
        yield metrics
    finally:
        _CURRENT_METRICS.reset(token)


def record_node_result(
    node_id: str,
    capability: str,
    before_state: Any,
    after_state: Any,
    duration_ms: int | None = None,
) -> None:
    metrics = _CURRENT_METRICS.get()
    if metrics is None:
        return

    summary = node_result_summary(after_state)
    event: RunMetrics = {
        "type": "node",
        "node_id": node_id,
        "capability": capability,
        "duration_ms": duration_ms,
        "ok": summary.get("ok"),
        "exit_code": summary.get("exit_code"),
        "result_paths": summary.get("result_paths", []),
        "artifact_count": summary.get("artifact_count", 0),
        "warning_count": summary.get("warning_count", 0),
    }
    approval = _approval_summary(after_state)
    if approval:
        event["approval"] = approval
    execution = _new_execution_summaries(before_state, after_state)
    if execution:
        event["execution_results"] = execution
    failure_signals = _new_failure_signals(before_state, after_state)
    if failure_signals:
        event["failure_signals"] = failure_signals
        event["warning_count"] = int(event.get("warning_count") or 0) + len(failure_signals)
    react_statuses = _new_react_statuses(before_state, after_state)
    if react_statuses:
        event["react_statuses"] = react_statuses
    metrics.append(event)

    if capability != "exec.codex_prompt":
        return

    before_results = _execution_results_by_path(before_state)
    after_results = _execution_results_by_path(after_state)
    for path, result in sorted(after_results.items()):
        if before_results.get(path) == result:
            continue
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            continue
        token_usage = metadata.get("token_usage")
        if not isinstance(token_usage, dict):
            continue
        metrics.append(
            {
                "type": "token_usage",
                "node_id": node_id,
                "capability": capability,
                "state_path": path,
                "instruction_id": result.get("instruction_id"),
                "ok": result.get("ok"),
                "exit_code": result.get("exit_code"),
                "token_usage": _normalize_usage(token_usage),
            }
        )


def update_state_run_metrics(
    node_id: str,
    capability: str,
    before_state: Any,
    after_state: Any,
    duration_ms: int | None = None,
) -> Any:
    if _CURRENT_METRICS.get() is None:
        return after_state
    if not isinstance(after_state, dict):
        return after_state

    next_state = dict(after_state)
    run_state = next_state.get("run")
    run = dict(run_state) if isinstance(run_state, dict) else {}
    run["node_timings"] = _append_node_timing(
        run.get("node_timings"),
        node_id,
        capability,
        duration_ms,
    )

    token_events = _new_token_usage_events(node_id, capability, before_state, after_state)
    if token_events:
        run["token_usage"] = _append_token_usage(run.get("token_usage"), token_events)

    next_state["run"] = run
    return next_state


def node_result_summary(value: Any) -> dict[str, Any]:
    results = _execution_results_by_path(value)
    failure_signals = _collect_failure_signals(value)
    result_paths = sorted(path for path in results if path)
    artifact_count = 0
    warning_count = len(failure_signals)
    ok_values: list[bool] = []
    exit_codes: list[Any] = []
    token_usage = _empty_usage()
    for result in results.values():
        ok = result.get("ok")
        if isinstance(ok, bool):
            ok_values.append(ok)
        exit_codes.append(result.get("exit_code"))
        artifacts = result.get("artifacts")
        if isinstance(artifacts, list):
            artifact_count += len(artifacts)
        stderr = result.get("stderr")
        if result.get("ok") is True and _is_warning_stderr(stderr):
            warning_count += 1
        metadata = result.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("token_usage"), dict):
            usage = _normalize_usage(metadata["token_usage"])
            for key in token_usage:
                token_usage[key] += usage.get(key, 0)
    summary: dict[str, Any] = {
        "ok": all(ok_values) if ok_values else None,
        "exit_code": _single_value(exit_codes),
        "result_paths": result_paths,
        "artifact_count": artifact_count,
        "warning_count": warning_count,
        "failure_signal_count": len(failure_signals),
    }
    if any(token_usage.values()):
        summary["token_usage"] = token_usage
    return {
        **summary,
    }


def run_summary(metrics: list[RunMetrics] | None) -> dict[str, Any]:
    nodes = [item for item in metrics or [] if item.get("type") == "node"]
    warnings: list[dict[str, Any]] = []
    seen_warnings: set[tuple[Any, Any, Any]] = set()
    approvals: list[dict[str, Any]] = []
    failure_signals: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    react_statuses: list[dict[str, Any]] = []
    for item in nodes:
        if item.get("warning_count"):
            for result in item.get("execution_results", []) or []:
                if not isinstance(result, dict) or not result.get("warning"):
                    continue
                preview = result.get("stderr_preview")
                key = (
                    result.get("stderr_path"),
                    result.get("state_path"),
                    tuple(preview) if isinstance(preview, list) else preview,
                )
                if key in seen_warnings:
                    continue
                seen_warnings.add(key)
                warnings.append(
                    {
                        "node_id": item.get("node_id"),
                        "capability": item.get("capability"),
                        "state_path": result.get("state_path"),
                        "stderr_size": result.get("stderr_size"),
                        "stderr_preview": result.get("stderr_preview"),
                        "stderr_path": result.get("stderr_path"),
                        "timeout": result.get("timeout"),
                    }
                )
        approval = item.get("approval")
        if isinstance(approval, dict):
            approvals.append(
                {
                    "node_id": item.get("node_id"),
                    "duration_ms": item.get("duration_ms"),
                    **approval,
                }
            )
        for signal in item.get("failure_signals", []) or []:
            if isinstance(signal, dict):
                failure_signals.append(
                    {
                        "node_id": item.get("node_id"),
                        "capability": item.get("capability"),
                        **signal,
                    }
                )
        for result in item.get("execution_results", []) or []:
            if not isinstance(result, dict):
                continue
            for artifact in result.get("artifacts", []) or []:
                if isinstance(artifact, dict):
                    artifacts.append(
                        {
                            "node_id": item.get("node_id"),
                            "state_path": result.get("state_path"),
                            **artifact,
                        }
                    )
        for status in item.get("react_statuses", []) or []:
            if isinstance(status, dict):
                react_statuses.append(
                    {
                        "node_id": item.get("node_id"),
                        "capability": item.get("capability"),
                        **status,
                    }
                )
    slow_nodes = sorted(
        nodes,
        key=lambda item: item.get("duration_ms") if isinstance(item.get("duration_ms"), int) else -1,
        reverse=True,
    )[:10]
    return {
        "nodes": nodes,
        "slow_nodes": slow_nodes,
        "warnings": warnings,
        "approvals": approvals,
        "failure_signals": failure_signals,
        "artifacts": artifacts,
        "react_statuses": react_statuses,
    }


def token_summary(metrics: list[RunMetrics] | None) -> dict[str, Any]:
    steps = []
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    for item in metrics or []:
        usage = item.get("token_usage")
        if not isinstance(usage, dict):
            continue
        normalized = _normalize_usage(usage)
        steps.append(
            {
                "node_id": item.get("node_id"),
                "capability": item.get("capability"),
                "state_path": item.get("state_path"),
                "instruction_id": item.get("instruction_id"),
                "ok": item.get("ok"),
                "exit_code": item.get("exit_code"),
                "token_usage": normalized,
            }
        )
        for key in totals:
            totals[key] += normalized.get(key, 0)

    return {
        "steps": steps,
        "totals": totals,
    }


def _append_node_timing(value: Any, node_id: str, capability: str, duration_ms: int | None) -> dict[str, Any]:
    steps = list(value.get("steps", [])) if isinstance(value, dict) and isinstance(value.get("steps"), list) else []
    safe_duration = duration_ms if isinstance(duration_ms, int) and duration_ms >= 0 else 0
    steps.append(
        {
            "node_id": node_id,
            "capability": capability,
            "duration_ms": safe_duration,
        }
    )
    total = 0
    for step in steps:
        if isinstance(step, dict) and isinstance(step.get("duration_ms"), int) and step["duration_ms"] >= 0:
            total += step["duration_ms"]
    return {
        "steps": steps,
        "node_count": len(steps),
        "total_duration_ms": total,
    }


def _append_token_usage(value: Any, events: list[dict[str, Any]]) -> dict[str, Any]:
    steps = list(value.get("steps", [])) if isinstance(value, dict) and isinstance(value.get("steps"), list) else []
    totals = _normalize_usage(value.get("totals", {})) if isinstance(value, dict) else _empty_usage()
    for event in events:
        usage = event["token_usage"]
        steps.append(event)
        for key in totals:
            totals[key] += usage.get(key, 0)
    return {
        "steps": steps,
        "totals": totals,
    }


def _new_token_usage_events(node_id: str, capability: str, before_state: Any, after_state: Any) -> list[dict[str, Any]]:
    before_results = _execution_results_by_path(before_state)
    after_results = _execution_results_by_path(after_state)
    events = []
    for path, result in sorted(after_results.items()):
        if before_results.get(path) == result:
            continue
        metadata = result.get("metadata")
        if not isinstance(metadata, dict):
            continue
        token_usage = metadata.get("token_usage")
        if not isinstance(token_usage, dict):
            continue
        events.append(
            {
                "node_id": node_id,
                "capability": capability,
                "state_path": path,
                "instruction_id": result.get("instruction_id"),
                "ok": result.get("ok"),
                "exit_code": result.get("exit_code"),
                "token_usage": _normalize_usage(token_usage),
            }
        )
    return events


def _new_execution_summaries(before_state: Any, after_state: Any) -> list[dict[str, Any]]:
    before_results = _execution_results_by_path(before_state)
    after_results = _execution_results_by_path(after_state)
    summaries = []
    for path, result in sorted(after_results.items()):
        if before_results.get(path) == result:
            continue
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        track_files = metadata.get("track_files") if isinstance(metadata.get("track_files"), dict) else {}
        stderr = result.get("stderr")
        stderr_text = stderr if isinstance(stderr, str) else ""
        stdout = result.get("stdout")
        stdout_text = stdout if isinstance(stdout, str) else ""
        warning = result.get("ok") is True and _is_warning_stderr(stderr_text)
        summaries.append(
            {
                "state_path": path,
                "instruction_id": result.get("instruction_id"),
                "ok": result.get("ok"),
                "exit_code": result.get("exit_code"),
                "stdout_size": len(stdout_text),
                "stderr_size": len(stderr_text),
                "stderr_preview": _preview_lines(stderr_text),
                "stderr_path": metadata.get("stderr_path") or track_files.get("stderr"),
                "stdout_path": metadata.get("stdout_path") or track_files.get("stdout"),
                "timeout": metadata.get("timeout"),
                "model": metadata.get("model"),
                "prompt_path": metadata.get("prompt_path") or metadata.get("main_prompt_path"),
                "context_paths": metadata.get("context_paths"),
                "artifacts": result.get("artifacts") if isinstance(result.get("artifacts"), list) else [],
                "warning": warning,
            }
        )
    return summaries


def _new_failure_signals(before_state: Any, after_state: Any) -> list[dict[str, Any]]:
    before_failures = _failure_signals_by_path(before_state)
    after_failures = _failure_signals_by_path(after_state)
    failures = []
    for path, item in sorted(after_failures.items()):
        if before_failures.get(path) == item:
            continue
        failures.append(
            {
                "state_path": path,
                "status": item.get("status"),
                "error_type": item.get("error_type"),
                "message": item.get("message"),
            }
        )
    return failures


def _new_react_statuses(before_state: Any, after_state: Any) -> list[dict[str, Any]]:
    before_statuses = _react_statuses_by_path(before_state)
    after_statuses = _react_statuses_by_path(after_state)
    statuses = []
    for path, item in sorted(after_statuses.items()):
        if before_statuses.get(path) == item:
            continue
        statuses.append(
            {
                "state_path": path,
                "exit_reason": item.get("exit_reason"),
                "rounds": item.get("rounds"),
                "continuations": item.get("continuations"),
                "max_steps": item.get("max_steps"),
                "extra_max_steps": item.get("extra_max_steps"),
            }
        )
    return statuses


def _react_statuses_by_path(value: Any) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    _collect_react_statuses_by_path(value, "", statuses)
    return statuses


def _collect_react_statuses_by_path(value: Any, path: str, statuses: dict[str, dict[str, Any]]) -> None:
    if (
        isinstance(value, dict)
        and isinstance(value.get("exit_reason"), str)
        and isinstance(value.get("rounds"), int)
        and isinstance(value.get("continuations"), int)
        and isinstance(value.get("max_steps"), int)
    ):
        statuses[path] = value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("__"):
                continue
            item_path = key if not path else f"{path}.{key}"
            _collect_react_statuses_by_path(item, item_path, statuses)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _collect_react_statuses_by_path(item, f"{path}[{index}]", statuses)


def _collect_failure_signals(value: Any) -> list[dict[str, Any]]:
    return list(_failure_signals_by_path(value).values())


def _failure_signals_by_path(value: Any) -> dict[str, dict[str, Any]]:
    failures: dict[str, dict[str, Any]] = {}
    _collect_failure_signals_by_path(value, "", failures)
    return failures


def _collect_failure_signals_by_path(value: Any, path: str, failures: dict[str, dict[str, Any]]) -> None:
    if (
        isinstance(value, dict)
        and value.get("status") == "failed"
        and isinstance(value.get("error_type"), str)
        and isinstance(value.get("message"), str)
    ):
        failures[path] = value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("__"):
                continue
            item_path = key if not path else f"{path}.{key}"
            _collect_failure_signals_by_path(item, item_path, failures)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _collect_failure_signals_by_path(item, f"{path}[{index}]", failures)


def _approval_summary(value: Any) -> dict[str, Any] | None:
    found: list[dict[str, Any]] = []
    _collect_approval_results(value, found)
    if not found:
        return None
    return found[-1]


def _collect_approval_results(value: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if isinstance(value.get("request_id"), str) and value.get("decision") in {"approve", "reject"}:
            found.append(
                {
                    "request_id": value.get("request_id"),
                    "decision": value.get("decision"),
                    "comment": value.get("comment", ""),
                }
            )
            return
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("__"):
                continue
            _collect_approval_results(item, found)
    elif isinstance(value, list):
        for item in value:
            _collect_approval_results(item, found)


def _preview_lines(text: str, max_lines: int = 3) -> list[str]:
    return [line.strip() for line in text.splitlines()[:max_lines] if line.strip()]


def _is_warning_stderr(stderr: Any) -> bool:
    if not isinstance(stderr, str):
        return False
    meaningful = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in _BENIGN_STDERR_PATTERNS:
            continue
        if any(stripped.startswith(prefix) for prefix in _BENIGN_STDERR_PREFIXES):
            continue
        meaningful.append(stripped)
    return bool(meaningful)


def _single_value(values: list[Any]) -> Any:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    first = clean[0]
    if all(value == first for value in clean):
        return first
    return clean


def _execution_results_by_path(value: Any) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    _collect_execution_results(value, "", results)
    return results


def _collect_execution_results(value: Any, path: str, results: dict[str, dict[str, Any]]) -> None:
    if _is_execution_result(value):
        results[path] = value
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("__"):
                continue
            item_path = key if not path else f"{path}.{key}"
            _collect_execution_results(item, item_path, results)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _collect_execution_results(item, f"{path}[{index}]", results)


def _is_execution_result(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("instruction_id"), str)
        and isinstance(value.get("metadata"), dict)
        and "ok" in value
        and "exit_code" in value
    )


def _normalize_usage(usage: dict[str, Any]) -> dict[str, int]:
    normalized = _empty_usage()
    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_input_tokens",
        "reasoning_output_tokens",
    ):
        value = usage.get(key, 0)
        if isinstance(value, int) and value >= 0:
            normalized[key] = value
        elif isinstance(value, float) and value >= 0:
            normalized[key] = int(value)
        else:
            normalized[key] = 0
    if normalized["total_tokens"] == 0:
        normalized["total_tokens"] = normalized["input_tokens"] + normalized["output_tokens"]
    return normalized


def _empty_usage() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_output_tokens": 0,
    }
