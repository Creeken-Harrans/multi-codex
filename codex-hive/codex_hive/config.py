"""Configuration loading."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field

from .constants import DEFAULT_CONFIG_FILENAME, DEFAULT_STATE_DIR
from .models import AgentProfile


class GeneralConfig(BaseModel):
    artifacts_dir: str = f"{DEFAULT_STATE_DIR}/runs"
    worktree_root: str = f"{DEFAULT_STATE_DIR}/worktrees"
    max_parallel_agents: int = 6
    default_strategy: str = "auto"
    default_timeout_seconds: int = 1800


class CodexConfig(BaseModel):
    binary: str = "codex"
    default_exec_args: list[str] = Field(default_factory=list)
    default_model: str = "gpt-5.4"
    default_reasoning_effort: str = "high"
    code_home: str | None = None


class GitConfig(BaseModel):
    base_branch: str = "main"
    auto_commit: bool = False
    auto_push: bool = False
    use_worktree_lock: bool = True
    serialize_git_ops: bool = True


class ConsensusConfig(BaseModel):
    debate_enabled: bool = True
    judge_enabled: bool = True
    confirmed_threshold: float = 0.75
    needs_verification_threshold: float = 0.4


class RecoveryConfig(BaseModel):
    persist_jsonl_events: bool = True
    resume_on_restart: bool = True


class VerificationConfig(BaseModel):
    auto_detect_commands: bool = True
    run_lint: bool = True
    run_typecheck: bool = True
    run_tests: bool = True


class AppConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    codex: CodexConfig = Field(default_factory=CodexConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    consensus: ConsensusConfig = Field(default_factory=ConsensusConfig)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)
    agents: dict[str, AgentProfile] = Field(default_factory=dict)

    @classmethod
    def from_path(cls, path: Path | None) -> "AppConfig":
        if path is None or not path.exists():
            return cls.default()
        return cls.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def default(cls) -> "AppConfig":
        agents = {
            "orchestrator": AgentProfile(name="orchestrator", role="orchestrator", read_only=True),
            "mission_keeper": AgentProfile(name="mission_keeper", role="mission_keeper", read_only=True),
            "planner": AgentProfile(name="planner", role="planner", read_only=True),
            "scout": AgentProfile(name="scout", role="scout", read_only=True),
            "architect": AgentProfile(name="architect", role="architect", read_only=True),
            "implementer": AgentProfile(name="implementer", role="implementer", read_only=False),
            "tester": AgentProfile(name="tester", role="tester", read_only=False),
            "reviewer": AgentProfile(name="reviewer", role="reviewer", read_only=True),
            "security_reviewer": AgentProfile(name="security_reviewer", role="security_reviewer", read_only=True),
            "performance_reviewer": AgentProfile(name="performance_reviewer", role="performance_reviewer", read_only=True),
            "maintainability_reviewer": AgentProfile(name="maintainability_reviewer", role="maintainability_reviewer", read_only=True),
            "judge": AgentProfile(name="judge", role="judge", read_only=True),
            "merger": AgentProfile(name="merger", role="merger", read_only=False),
        }
        return cls(agents=agents)

    def config_path(self, repo_root: Path) -> Path:
        return repo_root / DEFAULT_CONFIG_FILENAME

    def state_dir(self, repo_root: Path) -> Path:
        return repo_root / DEFAULT_STATE_DIR

    def codex_available(self) -> bool:
        return shutil.which(self.codex.binary) is not None


DEFAULT_CONFIG_TEXT = """
[general]
artifacts_dir = ".codex-hive/runs"
worktree_root = ".codex-hive/worktrees"
max_parallel_agents = 6
default_strategy = "auto"
default_timeout_seconds = 1800

[codex]
binary = "codex"
default_exec_args = []
default_model = "gpt-5.4"
default_reasoning_effort = "high"

[git]
base_branch = "main"
auto_commit = false
auto_push = false
use_worktree_lock = true
serialize_git_ops = true

[consensus]
debate_enabled = true
judge_enabled = true
confirmed_threshold = 0.75
needs_verification_threshold = 0.4

[recovery]
persist_jsonl_events = true
resume_on_restart = true

[verification]
auto_detect_commands = true
run_lint = true
run_typecheck = true
run_tests = true
""".strip()
