import lgwf.capabilities.subgraph.validation_sandbox.capability as capability_module


CAPABILITY = capability_module.CAPABILITY


def register_into(registry_module) -> None:
    registry_module.register(CAPABILITY)
