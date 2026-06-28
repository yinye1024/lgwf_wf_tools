import lgwf_dsl.diagnostics as diagnostics_module


class DSLError(ValueError):
    """Base class for LGWF text DSL errors."""

    def __init__(
        self,
        message: str,
        location: diagnostics_module.SourceLocation | None = None,
        *,
        code: str = "LGWF_DSL_ERROR",
        suggestion: str | None = None,
    ) -> None:
        self.message = message
        self.location = location
        self.code = code
        self.suggestion = suggestion
        diagnostic = diagnostics_module.Diagnostic(message, location)
        super().__init__(diagnostic.format())


class DSLParseError(DSLError):
    """Raised when text DSL syntax is invalid."""


class DSLValidationError(DSLError):
    """Raised when parsed text DSL semantics are invalid."""
