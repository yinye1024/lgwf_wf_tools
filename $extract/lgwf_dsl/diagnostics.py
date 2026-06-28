from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    source_name: str | None
    line: int
    column: int
    offset: int

    def format(self) -> str:
        if self.source_name:
            return f"{self.source_name}:{self.line}:{self.column}"
        return f"{self.line}:{self.column}"


@dataclass(frozen=True)
class SourceSpan:
    start: SourceLocation
    end: SourceLocation


@dataclass(frozen=True)
class Diagnostic:
    message: str
    location: SourceLocation | None = None
    severity: str = "warning"
    code: str = "LGWF_LINT"
    suggestion: str | None = None

    def format(self) -> str:
        if self.location is None:
            return self.message
        return f"{self.location.format()}: {self.message}"

    def to_dict(self) -> dict[str, str]:
        data = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.location is not None:
            data["location"] = self.location.format()
        if self.suggestion is not None:
            data["suggestion"] = self.suggestion
        return data
