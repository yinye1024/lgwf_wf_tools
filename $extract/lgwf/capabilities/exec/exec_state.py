import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.types as capability_types


def public_state(state: capability_types.State) -> capability_types.State:
    return {
        key: value
        for key, value in state.items()
        if not route_key_module.is_route_key(key)
    }

