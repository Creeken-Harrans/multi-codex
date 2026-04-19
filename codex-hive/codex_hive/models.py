"""Pydantic models for codex-hive."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    blocked = "blocked"
    running = "running"
    retrying = "retrying"
    awaiting_approval = "awaiting-approval"
    awaiting_merge = "awaiting-merge"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    escalated = "escalated"


class TaskType(str, Enum):
    exploration = "exploration"
    implementation = "implementation"
    refactor = "refactor"
    review = "review"
    bugfix = "bugfix"
    test_generation = "test_generation"
    documentation = "documentation"
    migration = "migration"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ConsensusLevel(str, Enum):
    confirmed = "confirmed"
    needs_verification = "needs_verification"
    unverified = "unverified"


class WorkerStatus(str, Enum):
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"
    cancelled = "cancelled"


class EventRecord(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    event_type: str
    run_id: str
    task_id: str | None = None
    payload: dict = Field(default_factory=dict)


class AcceptanceCriteria(BaseModel):
    description: str
    mandatory: bool = True
    evidence_hint: str | None = None


class MissionSpec(BaseModel):
    mission: str
    scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriteria] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.medium


class TaskSpec(BaseModel):
    task_id: str
    title: str
    description: str
    type: TaskType
    role: str
    dependencies: list[str] = Field(default_factory=list)
    owned_paths: list[str] = Field(default_factory=list)
    read_paths: list[str] = Field(default_factory=list)
    write_enabled: bool = False
    strategy: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class TaskAssignment(BaseModel):
    run_id: str
    task: TaskSpec
    agent_id: str
    worktree_path: str | None = None
    branch_name: str | None = None


class WorkerPromptEnvelope(BaseModel):
    assignment: TaskAssignment
    mission: MissionSpec
    role_instructions: str
    context_files: list[str] = Field(default_factory=list)
    diff_summary: str | None = None
    verification_summary: str | None = None
    output_contract: str = "Return JSON matching WorkerResult."


class ReviewFinding(BaseModel):
    finding_id: str
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"] = "medium"
    category: Literal["bug", "risk", "suggestion"] = "bug"
    description: str
    evidence: list[str] = Field(default_factory=list)
    reproduction: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_agent_id: str | None = None


class ChangeProposal(BaseModel):
    summary: str
    files_changed: list[str] = Field(default_factory=list)
    patch_summary: list[str] = Field(default_factory=list)
    rationale: str | None = None


class WorkerResult(BaseModel):
    task_id: str
    agent_id: str
    role: str
    status: WorkerStatus
    summary: str
    assumptions: list[str] = Field(default_factory=list)
    files_read: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suggested_next_steps: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    branch_name: str | None = None
    worktree_path: str | None = None
    change_proposal: ChangeProposal | None = None
    metadata: dict = Field(default_factory=dict)


class ConsensusFinding(BaseModel):
    canonical_key: str
    title: str
    normalized_description: str
    severity: str
    evidence: list[str] = Field(default_factory=list)
    source_agents: list[str] = Field(default_factory=list)
    agreement_ratio: float = 0.0
    max_confidence: float = 0.0
    consensus_score: float = 0.0
    consensus_level: ConsensusLevel = ConsensusLevel.unverified


class ConsensusReport(BaseModel):
    findings: list[ConsensusFinding] = Field(default_factory=list)
    debate_rounds: int = 0
    blind_judge_summary: str | None = None
    overall_score: float = 0.0


class MergePlan(BaseModel):
    run_id: str
    branch_order: list[str] = Field(default_factory=list)
    merge_actions: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    verification_required: list[str] = Field(default_factory=list)


class MissionCheckResult(BaseModel):
    goal_alignment_score: float = Field(ge=0.0, le=1.0)
    scope_violations: list[str] = Field(default_factory=list)
    missing_acceptance_items: list[str] = Field(default_factory=list)
    unjustified_extra_changes: list[str] = Field(default_factory=list)
    passed: bool = True


class RunReport(BaseModel):
    run_id: str
    mission: MissionSpec
    status: RunStatus
    strategy: str
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    tasks: list[TaskSpec] = Field(default_factory=list)
    worker_results: list[WorkerResult] = Field(default_factory=list)
    consensus_report: ConsensusReport | None = None
    merge_plan: MergePlan | None = None
    mission_check: MissionCheckResult | None = None
    final_summary: str = ""


class VerificationCommand(BaseModel):
    command: list[str]
    reason: str


class VerificationResult(BaseModel):
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    skipped: bool = False
    reason: str | None = None


class AgentProfile(BaseModel):
    name: str
    role: str
    model: str = "gpt-5.4"
    reasoning_effort: str = "high"
    sandbox_mode: str = "workspace-write"
    timeout_seconds: int = 1800
    read_only: bool = True
    strategy_preference: str | None = None
    return_format: str = "json"


class RunRecord(BaseModel):
    run_id: str
    mission: str
    strategy: str
    status: RunStatus
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    repo_root: str
    artifacts_dir: str


class StoredTaskRecord(BaseModel):
    run_id: str
    task_id: str
    role: str
    status: RunStatus
    payload: dict = Field(default_factory=dict)


class AgentExecutionRecord(BaseModel):
    run_id: str
    task_id: str
    agent_id: str
    role: str
    status: str
    adapter: str
    worktree_path: str | None = None
    branch_name: str | None = None
    result_path: str | None = None


class OwnershipDecision(BaseModel):
    parallel_safe: bool
    overlapping_paths: list[str] = Field(default_factory=list)
    serialized_groups: list[list[str]] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    mission: MissionSpec
    tasks: list[TaskSpec]
    strategy: str
    ownership: OwnershipDecision
    notes: list[str] = Field(default_factory=list)


class RepoHealth(BaseModel):
    repo_root: str
    git_available: bool
    codex_available: bool
    config_found: bool
    writable_state_dir: bool


class ArtifactIndex(BaseModel):
    run_dir: str
    files: list[str] = Field(default_factory=list)
