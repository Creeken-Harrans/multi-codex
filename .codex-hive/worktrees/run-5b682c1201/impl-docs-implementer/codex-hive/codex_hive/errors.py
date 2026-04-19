"""Custom errors."""

from __future__ import annotations


class CodexHiveError(Exception):
    """Base error for codex-hive."""


class ConfigurationError(CodexHiveError):
    """Invalid or missing configuration."""


class GitOperationError(CodexHiveError):
    """Git operation failed."""


class RetryableAgentError(CodexHiveError):
    """An agent task can be retried."""


class NonRetryableAgentError(CodexHiveError):
    """An agent task cannot be retried safely."""


class MissionDriftError(CodexHiveError):
    """Mission keeper rejected the run outcome."""
