"""Verification command detection."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..models import VerificationCommand


VERIFICATION_CANDIDATES = [
    (["make", "test"], "make test"),
    (["pytest"], "pytest"),
    (["pnpm", "test"], "pnpm test"),
    (["npm", "test"], "npm test"),
    (["cargo", "test"], "cargo test"),
    (["go", "test", "./..."], "go test"),
    (["ruff", "check", "."], "ruff"),
    (["mypy", "."], "mypy"),
    (["tsc", "--noEmit"], "tsc"),
    (["pnpm", "lint"], "pnpm lint"),
    (["npm", "run", "lint"], "npm run lint"),
    (["cargo", "clippy"], "cargo clippy"),
]


def detect_commands(repo_root: Path) -> list[VerificationCommand]:
    del repo_root
    detected: list[VerificationCommand] = []
    for command, reason in VERIFICATION_CANDIDATES:
        if shutil.which(command[0]):
            detected.append(VerificationCommand(command=command, reason=reason))
    return detected
