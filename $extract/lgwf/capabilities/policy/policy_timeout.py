import asyncio
import inspect
from typing import Any

import lgwf.capabilities.types as capability_types
import lgwf.capabilities.policy.types as policy_types


class NodeTimeoutError(TimeoutError):
    """Raised when an LGWF node exceeds policy.timeout."""


class PolicyTimeoutCapability:
    name = "policy.timeout"

    def create_kwargs(self, config: dict[str, Any]) -> policy_types.PolicyKwargs:
        run_timeout = config.get("run_timeout")
        idle_timeout = config.get("idle_timeout")
        refresh_on = config.get("refresh_on", "auto")

        if run_timeout is None and idle_timeout is None:
            raise ValueError("policy.timeout requires run_timeout or idle_timeout.")
        if run_timeout is not None and (not isinstance(run_timeout, int | float) or run_timeout <= 0):
            raise ValueError("policy.timeout run_timeout must be a number > 0 when provided.")
        if idle_timeout is not None and (not isinstance(idle_timeout, int | float) or idle_timeout <= 0):
            raise ValueError("policy.timeout idle_timeout must be a number > 0 when provided.")
        if refresh_on not in {"auto", "heartbeat"}:
            raise ValueError("policy.timeout refresh_on must be 'auto' or 'heartbeat'.")

        timeout = float(run_timeout if run_timeout is not None else idle_timeout)

        def wrap_node(node: capability_types.NodeCallable) -> capability_types.NodeCallable:
            if not inspect.iscoroutinefunction(node):
                raise ValueError("policy.timeout supports async nodes only.")

            async def wrapped(state: capability_types.State) -> capability_types.State:
                try:
                    return await asyncio.wait_for(node(state), timeout=timeout)
                except TimeoutError as exc:
                    raise NodeTimeoutError(f"Node exceeded timeout of {timeout} seconds.") from exc

            return wrapped

        return {
            "__lgwf_node_wrappers": [wrap_node],
        }


CAPABILITY = PolicyTimeoutCapability()

