"""SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import AgentExecutionRecord, RunRecord, StoredTaskRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  mission TEXT NOT NULL,
  strategy TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  repo_root TEXT NOT NULL,
  artifacts_dir TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
  run_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (run_id, task_id)
);
CREATE TABLE IF NOT EXISTS executions (
  run_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  adapter TEXT NOT NULL,
  worktree_path TEXT,
  branch_name TEXT,
  result_path TEXT,
  PRIMARY KEY (run_id, task_id, agent_id)
);
"""


class StateDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def upsert_run(self, record: RunRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
              mission=excluded.mission,
              strategy=excluded.strategy,
              status=excluded.status,
              updated_at=excluded.updated_at,
              repo_root=excluded.repo_root,
              artifacts_dir=excluded.artifacts_dir
            """,
            (
                record.run_id,
                record.mission,
                record.strategy,
                record.status.value,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.repo_root,
                record.artifacts_dir,
            ),
        )
        self.connection.commit()

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self.connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return RunRecord.model_validate(dict(row))

    def list_runs(self) -> list[RunRecord]:
        rows = self.connection.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        return [RunRecord.model_validate(dict(row)) for row in rows]

    def upsert_task(self, record: StoredTaskRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO tasks VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id, task_id) DO UPDATE SET
              role=excluded.role,
              status=excluded.status,
              payload=excluded.payload
            """,
            (record.run_id, record.task_id, record.role, record.status.value, json.dumps(record.payload)),
        )
        self.connection.commit()

    def list_tasks(self, run_id: str) -> list[StoredTaskRecord]:
        rows = self.connection.execute("SELECT * FROM tasks WHERE run_id = ?", (run_id,)).fetchall()
        return [
            StoredTaskRecord(
                run_id=row["run_id"],
                task_id=row["task_id"],
                role=row["role"],
                status=row["status"],
                payload=json.loads(row["payload"]),
            )
            for row in rows
        ]

    def upsert_execution(self, record: AgentExecutionRecord) -> None:
        self.connection.execute(
            """
            INSERT INTO executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, task_id, agent_id) DO UPDATE SET
              role=excluded.role,
              status=excluded.status,
              adapter=excluded.adapter,
              worktree_path=excluded.worktree_path,
              branch_name=excluded.branch_name,
              result_path=excluded.result_path
            """,
            (
                record.run_id,
                record.task_id,
                record.agent_id,
                record.role,
                record.status,
                record.adapter,
                record.worktree_path,
                record.branch_name,
                record.result_path,
            ),
        )
        self.connection.commit()

    def list_executions(self, run_id: str) -> list[AgentExecutionRecord]:
        rows = self.connection.execute("SELECT * FROM executions WHERE run_id = ?", (run_id,)).fetchall()
        return [AgentExecutionRecord.model_validate(dict(row)) for row in rows]
