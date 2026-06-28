from typing import Any

from langgraph.types import RetryPolicy

import lgwf.capabilities.policy.types as policy_types


class PolicyRetryCapability:
    name = "policy.retry"

    def create_kwargs(self, config: dict[str, Any]) -> policy_types.PolicyKwargs:
        max_attempts = config.get("max_attempts", 3)
        initial_interval = config.get("initial_interval", 0.5)
        backoff_factor = config.get("backoff_factor", 2.0)
        max_interval = config.get("max_interval", 128.0)
        jitter = config.get("jitter", True)

        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("policy.retry requires max_attempts to be an integer >= 1.")
        if not isinstance(initial_interval, int | float) or initial_interval < 0:
            raise ValueError("policy.retry requires initial_interval to be a number >= 0.")
        if not isinstance(backoff_factor, int | float) or backoff_factor < 1:
            raise ValueError("policy.retry requires backoff_factor to be a number >= 1.")
        if not isinstance(max_interval, int | float) or max_interval < 0:
            raise ValueError("policy.retry requires max_interval to be a number >= 0.")
        if not isinstance(jitter, bool):
            raise ValueError("policy.retry requires jitter to be a boolean.")

        return {
            "retry_policy": RetryPolicy(
                max_attempts=max_attempts,
                initial_interval=float(initial_interval),
                backoff_factor=float(backoff_factor),
                max_interval=float(max_interval),
                jitter=jitter,
                retry_on=Exception,
            )
        }


CAPABILITY = PolicyRetryCapability()

