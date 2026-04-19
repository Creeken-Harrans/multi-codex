"""Resume helpers."""

from __future__ import annotations

from ..db import StateDB
from ..models import RunRecord, RunStatus


class ResumeManager:
    def __init__(self, db: StateDB) -> None:
        self.db = db

    def resumable_runs(self) -> list[RunRecord]:
        return [record for record in self.db.list_runs() if record.status in {RunStatus.running, RunStatus.retrying, RunStatus.awaiting_merge, RunStatus.failed}]
