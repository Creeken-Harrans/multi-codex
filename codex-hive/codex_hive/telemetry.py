"""Lightweight telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass(slots=True)
class Timer:
    started_at: float = field(default_factory=monotonic)

    def elapsed(self) -> float:
        return monotonic() - self.started_at
