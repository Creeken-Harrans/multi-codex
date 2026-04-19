"""Conflict helpers."""

from __future__ import annotations

from pathlib import Path


def detect_conflict_markers(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return "<<<<<<<" in text and ">>>>>>>" in text
