import contextlib
import contextvars
from typing import Any

import lgwf_client.client_factory as client_factory_module


_CURRENT_CLIENT: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "lgwf_current_client",
    default=None,
)
_DEFAULT_CLIENT: Any | None = None


def get_client() -> Any:
    current_client = _CURRENT_CLIENT.get()
    if current_client is not None:
        return current_client

    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = client_factory_module.create_default_client()
    return _DEFAULT_CLIENT


@contextlib.contextmanager
def use_client(client: Any):
    token = _CURRENT_CLIENT.set(client)
    try:
        yield
    finally:
        _CURRENT_CLIENT.reset(token)

