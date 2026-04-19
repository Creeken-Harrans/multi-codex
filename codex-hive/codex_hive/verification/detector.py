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
    detected: list[VerificationCommand] = []
    for command, reason in VERIFICATION_CANDIDATES:
        if shutil.which(command[0]) and _repo_supports_command(repo_root, command):
            detected.append(VerificationCommand(command=command, reason=reason))
    return detected


def _repo_supports_command(repo_root: Path, command: list[str]) -> bool:
    binary = command[0]
    if binary == "pytest":
        return any((repo_root / name).exists() for name in ("tests", "pyproject.toml", "pytest.ini"))
    if binary == "make":
        return (repo_root / "Makefile").exists()
    if binary in {"npm", "pnpm"}:
        return any((repo_root / name).exists() for name in ("package.json", "pnpm-lock.yaml"))
    if binary == "cargo":
        return (repo_root / "Cargo.toml").exists()
    if binary == "go":
        return any((repo_root / name).exists() for name in ("go.mod", "go.work"))
    if binary == "ruff":
        return any((repo_root / name).exists() for name in ("pyproject.toml", "ruff.toml", ".ruff.toml"))
    if binary == "mypy":
        return any((repo_root / name).exists() for name in ("pyproject.toml", "mypy.ini", ".mypy.ini"))
    if binary == "tsc":
        return (repo_root / "tsconfig.json").exists()
    return True
