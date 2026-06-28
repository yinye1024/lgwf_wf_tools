import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Timer:
    started_at: float

    @classmethod
    def start(cls) -> "Timer":
        return cls(started_at=time.perf_counter())

    def elapsed_ms(self) -> int:
        return elapsed_ms(self.started_at)


def elapsed_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))


def duration_field(started_at: float) -> str:
    return f"duration_ms={elapsed_ms(started_at)}"


def step_message(prefix: str, step: str, started_at: float, **fields: object) -> str:
    parts = [prefix, f"step={step}", duration_field(started_at)]
    for key, value in fields.items():
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def emit_step(
    writer: Callable[[str], None] | None,
    prefix: str,
    step: str,
    started_at: float,
    **fields: object,
) -> None:
    if writer is not None:
        writer(step_message(prefix, step, started_at, **fields))
