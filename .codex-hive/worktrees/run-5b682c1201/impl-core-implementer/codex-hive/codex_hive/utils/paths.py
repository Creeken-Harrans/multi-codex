"""Path helpers."""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_repo_root(path: Path | None = None) -> Path:
    return (path or Path.cwd()).resolve()
