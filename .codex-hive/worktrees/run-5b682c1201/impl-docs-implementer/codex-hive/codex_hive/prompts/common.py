"""Shared prompt fragments."""

from __future__ import annotations


def json_contract(contract_name: str) -> str:
    return f"Return strict JSON matching {contract_name}. No markdown."


def role_guardrails(role: str, read_only: bool) -> str:
    mode = "read-only" if read_only else "write-enabled"
    return f"Role={role}. Mode={mode}. Stay within assigned scope. Do not invent verification."
