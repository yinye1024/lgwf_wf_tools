from typing import Any, Protocol


PolicyKwargs = dict[str, Any]


class Policy(Protocol):
    name: str

    def create_kwargs(self, config: dict[str, Any]) -> PolicyKwargs:
        ...

