"""JSONL event logging."""

from __future__ import annotations

import json
from pathlib import Path

from .models import EventRecord


class EventLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: EventRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def read_all(self) -> list[EventRecord]:
        if not self.path.exists():
            return []
        records: list[EventRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(EventRecord.model_validate_json(line))
        return records
