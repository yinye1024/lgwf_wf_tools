from typing import Any

from .capability import CAPABILITY


def register_into(registry_module: Any) -> None:
    registry_module.register(CAPABILITY)
