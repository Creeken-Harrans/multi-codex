"""Serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)


def write_json(path: Path, data: Any) -> None:
    path.write_text(to_json(data), encoding="utf-8")
