from typing import Any

import lgwf.capabilities.policy.policy_fallback as policy_fallback_module
import lgwf.capabilities.policy.policy_retry as policy_retry_module
import lgwf.capabilities.policy.policy_timeout as policy_timeout_module
import lgwf.capabilities.policy.types as policy_types


_POLICIES: list[policy_types.Policy] = [
    policy_fallback_module.CAPABILITY,
    policy_retry_module.CAPABILITY,
    policy_timeout_module.CAPABILITY,
]


REGISTRY: dict[str, policy_types.Policy] = {
    policy.name: policy for policy in _POLICIES
}


def has_policy(policy: str) -> bool:
    return policy in REGISTRY


def create_kwargs(policy: str, config: dict[str, Any] | None = None) -> policy_types.PolicyKwargs:
    try:
        entry = REGISTRY[policy]
    except KeyError as exc:
        raise ValueError(f"Unknown policy: {policy}") from exc

    return entry.create_kwargs(config or {})

