import contextlib
import contextvars
import copy
import inspect
from collections.abc import Callable
from typing import Any

import lgwf.capabilities.types as capability_types
import lgwf.runs.metrics as run_metrics_module
import lgwf_tools.timing as timing_module


ProgressWriter = Callable[[str], None]

_WRITER: contextvars.ContextVar[ProgressWriter | None] = contextvars.ContextVar(
    "lgwf_progress_writer",
    default=None,
)
_LAST_FAILURE: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "lgwf_last_failure",
    default=None,
)
_RUN_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "lgwf_progress_run_id",
    default=None,
)


@contextlib.contextmanager
def use_progress_writer(writer: ProgressWriter | None):
    token = _WRITER.set(writer)
    try:
        yield
    finally:
        _WRITER.reset(token)


@contextlib.contextmanager
def use_run_id(run_id: str | None):
    token = _RUN_ID.set(run_id)
    try:
        yield
    finally:
        _RUN_ID.reset(token)


def emit(message: str) -> None:
    writer = _WRITER.get()
    if writer is not None:
        writer(with_run_id(message))


def with_run_id(message: str, run_id: str | None = None) -> str:
    effective_run_id = run_id if run_id is not None else _RUN_ID.get()
    if not effective_run_id or "run_id=" in message:
        return message
    return f"{message} run_id={effective_run_id}"


@contextlib.contextmanager
def capture_failures():
    token = _LAST_FAILURE.set(None)
    try:
        yield
    finally:
        _LAST_FAILURE.reset(token)


def last_failure() -> dict[str, str] | None:
    return _LAST_FAILURE.get()


def wrap_node(
    node_id: str,
    capability: str,
    node: capability_types.NodeCallable,
) -> capability_types.NodeCallable:
    if inspect.iscoroutinefunction(node):
        async def async_wrapped(state: capability_types.State) -> capability_types.State:
            timer = timing_module.Timer.start()
            _emit_started(node_id, capability)
            before_state = copy.deepcopy(state)
            try:
                result = await node(state)
            except Exception as exc:
                _attach_failure(exc, node_id, capability)
                _emit_failed(node_id, capability, exc, timer.elapsed_ms())
                raise
            duration_ms = timer.elapsed_ms()
            result = run_metrics_module.update_state_run_metrics(node_id, capability, before_state, result, duration_ms)
            run_metrics_module.record_node_result(node_id, capability, before_state, result, duration_ms)
            _emit_completed(node_id, capability, result, duration_ms)
            return result

        return async_wrapped

    def wrapped(state: capability_types.State) -> capability_types.State:
        timer = timing_module.Timer.start()
        _emit_started(node_id, capability)
        before_state = copy.deepcopy(state)
        try:
            result = node(state)
        except Exception as exc:
            _attach_failure(exc, node_id, capability)
            _emit_failed(node_id, capability, exc, timer.elapsed_ms())
            raise
        duration_ms = timer.elapsed_ms()
        result = run_metrics_module.update_state_run_metrics(node_id, capability, before_state, result, duration_ms)
        run_metrics_module.record_node_result(node_id, capability, before_state, result, duration_ms)
        _emit_completed(node_id, capability, result, duration_ms)
        return result

    return wrapped


def _emit_started(node_id: str, capability: str) -> None:
    emit(f"[workflow] node started id={node_id} capability={capability}")


def _emit_failed(node_id: str, capability: str, exc: Exception, duration_ms: int) -> None:
    _LAST_FAILURE.set(
        {
            "node_id": node_id,
            "capability": capability,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    )
    emit(
        f"[workflow] node failed id={node_id} capability={capability} "
        f"duration_ms={duration_ms} error={type(exc).__name__}: {exc}"
    )


def _attach_failure(exc: Exception, node_id: str, capability: str) -> None:
    setattr(
        exc,
        "__lgwf_failure__",
        {
            "node_id": node_id,
            "capability": capability,
            "error_type": type(exc).__name__,
            "message": str(exc),
        },
    )


def _emit_completed(node_id: str, capability: str, result: Any, duration_ms: int) -> None:
    summary = run_metrics_module.node_result_summary(result)
    token_fields = _token_fields(summary.get("token_usage"))
    emit(
        f"[workflow] node completed id={node_id} capability={capability} "
        f"duration_ms={duration_ms} ok={_field(summary.get('ok'))} "
        f"exit_code={_field(summary.get('exit_code'))} "
        f"result_paths={_field(summary.get('result_paths'))} "
        f"artifact_count={summary.get('artifact_count', 0)} "
        f"warning_count={summary.get('warning_count', 0)}"
        f"{token_fields}"
    )


def _field(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ",".join(str(item) for item in value[:5]) + (",..." if len(value) > 5 else "") + "]"
    return value


def _token_fields(token_usage: Any) -> str:
    if not isinstance(token_usage, dict):
        return ""
    total = token_usage.get("total_tokens")
    if not isinstance(total, int) or total <= 0:
        return ""
    return (
        f" token_total={total}"
        f" token_input={_int_field(token_usage.get('input_tokens'))}"
        f" token_output={_int_field(token_usage.get('output_tokens'))}"
        f" token_cached={_int_field(token_usage.get('cached_input_tokens'))}"
        f" token_reasoning={_int_field(token_usage.get('reasoning_output_tokens'))}"
    )


def _int_field(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0

