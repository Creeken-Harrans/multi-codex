"""Cancellation helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CancellationToken:
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True
