from dataclasses import dataclass
from enum import Enum

import lgwf_dsl.diagnostics as diagnostics_module


class TokenKind(Enum):
    IDENT = "ident"
    STRING = "string"
    SYMBOL = "symbol"
    EOF = "eof"


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str
    location: diagnostics_module.SourceLocation
