"""Simple file locks for git operations."""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path


class FileLock:
    def __init__(self, path: Path, timeout_seconds: float = 10.0, stale_after_seconds: float = 600.0) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self.stale_after_seconds = stale_after_seconds

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout_seconds
        while True:
            try:
                fd = self.path.open("x", encoding="utf-8")
                fd.write(str(time.time()))
                fd.close()
                return
            except FileExistsError:
                try:
                    created = float(self.path.read_text(encoding="utf-8").strip())
                except Exception:
                    created = 0
                if time.time() - created > self.stale_after_seconds:
                    self.path.unlink(missing_ok=True)
                    continue
                if time.time() >= deadline:
                    raise TimeoutError(f"Timed out waiting for lock: {self.path}")
                time.sleep(0.05)

    def release(self) -> None:
        self.path.unlink(missing_ok=True)

    @contextmanager
    def held(self):
        self.acquire()
        try:
            yield self
        finally:
            self.release()
