"""Top-level orchestrator."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..adapters.base import AgentAdapter
from ..artifacts.writer import ArtifactWriter
from ..config import AppConfig
from ..consensus.blind_judge import judge_best
from ..consensus.debate_round import apply_debate_round
from ..consensus.merge_findings import merge_findings
from ..db import StateDB
from ..eventlog import EventLogger
from ..git.merge import Merger
from ..git.ops_queue import GitOpQueue
from ..git.ownership import analyze_ownership
from ..git.worktrees import WorktreeManager
from ..models import (
    AgentExecutionRecord,
    EventRecord,
    MissionSpec,
    PlannerOutput,
    RunRecord,
    RunReport,
    RunStatus,
    StoredTaskRecord,
    TaskAssignment,
    TaskSpec,
    TaskType,
    WorkerPromptEnvelope,
    WorkerResult,
    WorkerStatus,
)
from ..prompts import architect, implementer, maintainability_reviewer, mission_keeper, performance_reviewer, planner, reviewer, scout, security_reviewer, tester
from ..runtime.dispatcher import Dispatcher
from ..runtime.scheduler import Scheduler
from ..runtime.state_machine import StateMachine
from ..utils.hashing import stable_hash
from ..verification.detector import detect_commands
from ..verification.mission_guard import MissionKeeper
from ..verification.runner import run_verification


ROLE_PROMPTS = {
    "planner": planner.PROMPT,
    "scout": scout.PROMPT,
    "architect": architect.PROMPT,
    "implementer": implementer.PROMPT,
    "tester": tester.PROMPT,
    "reviewer": reviewer.PROMPT,
    "security_reviewer": security_reviewer.PROMPT,
    "performance_reviewer": performance_reviewer.PROMPT,
    "maintainability_reviewer": maintainability_reviewer.PROMPT,
    "mission_keeper": mission_keeper.PROMPT,
}


class Orchestrator:
    def __init__(
        self,
        repo_root: Path,
        config: AppConfig,
        db: StateDB,
        event_logger: EventLogger,
        adapter: AgentAdapter,
    ) -> None:
        self.repo_root = repo_root
        self.config = config
        self.db = db
        self.event_logger = event_logger
        self.adapter = adapter
        self.dispatcher = Dispatcher(adapter)
        self.scheduler = Scheduler()
        self.state_machine = StateMachine()
        self.worktrees = WorktreeManager(repo_root, repo_root / config.general.worktree_root)
        self.git_queue = GitOpQueue(repo_root / ".codex-hive" / "locks" / "git.lock")
        self.merger = Merger(repo_root)
        self.mission_keeper = MissionKeeper()

    def create_run_id(self, task: str) -> str:
        return f"run-{stable_hash(task + str(datetime.now(timezone.utc).timestamp()), length=10)}"

    def parse_mission(self, task: str) -> MissionSpec:
        lowered = task.lower()
        task_type = TaskType.implementation
        risk = "medium"
        if "review" in lowered:
            task_type = TaskType.review
        elif "bug" in lowered or "fix" in lowered:
            task_type = TaskType.bugfix
        elif "doc" in lowered:
            task_type = TaskType.documentation
        if "auth" in lowered or "oauth" in lowered or "security" in lowered:
            risk = "high"
        deliverables = ["source code", "tests", "documentation", "artifacts"]
        scope = ["codex_hive", "README.md", "docs", "tests", ".codex", "AGENTS.md", "examples"]
        acceptance = [
            {"description": "source code", "mandatory": True},
            {"description": "tests", "mandatory": True},
            {"description": "documentation", "mandatory": True},
        ]
        return MissionSpec.model_validate(
            {
                "mission": task,
                "scope": scope,
                "out_of_scope": [".git", ".venv"],
                "constraints": ["use worktree isolation for write-heavy tasks", "persist state in sqlite and jsonl"],
                "deliverables": deliverables,
                "acceptance_criteria": acceptance,
                "risk_level": risk,
            }
        )

    def plan(self, mission: MissionSpec, requested_strategy: str | None = None) -> PlannerOutput:
        tasks: list[TaskSpec] = [
            TaskSpec(task_id="plan", title="Plan mission", description=mission.mission, type=TaskType.exploration, role="planner", read_paths=["."], metadata={"confidence": 0.8}),
            TaskSpec(task_id="scout", title="Scout repository", description="Collect relevant files and commands", type=TaskType.exploration, role="scout", dependencies=["plan"], read_paths=["."], metadata={"confidence": 0.75}),
            TaskSpec(task_id="architect", title="Architect solution", description="Define interfaces and structure", type=TaskType.refactor, role="architect", dependencies=["scout"], read_paths=["codex_hive"], metadata={"confidence": 0.72}),
            TaskSpec(task_id="impl-core", title="Implement core runtime", description="Write core code", type=TaskType.implementation, role="implementer", dependencies=["architect"], owned_paths=["codex_hive/runtime/generated_core.py"], read_paths=["codex_hive"], write_enabled=True, metadata={"confidence": 0.8}),
            TaskSpec(task_id="impl-docs", title="Write docs", description="Update docs and README", type=TaskType.documentation, role="implementer", dependencies=["architect"], owned_paths=["docs/generated.md"], read_paths=["docs"], write_enabled=True, metadata={"confidence": 0.78}),
            TaskSpec(task_id="test", title="Verify changes", description="Run verification and tests", type=TaskType.test_generation, role="tester", dependencies=["impl-core", "impl-docs"], owned_paths=["tests/generated_test_placeholder.txt"], write_enabled=True, metadata={"confidence": 0.81}),
            TaskSpec(task_id="review-correctness", title="Correctness review", description="Review implementation", type=TaskType.review, role="reviewer", dependencies=["test"], read_paths=["codex_hive"], metadata={"confidence": 0.67}),
            TaskSpec(task_id="review-security", title="Security review", description="Review security", type=TaskType.review, role="security_reviewer", dependencies=["test"], read_paths=["codex_hive"], metadata={"confidence": 0.71}),
            TaskSpec(task_id="review-performance", title="Performance review", description="Review performance", type=TaskType.review, role="performance_reviewer", dependencies=["test"], read_paths=["codex_hive"], metadata={"confidence": 0.64}),
            TaskSpec(task_id="review-maintainability", title="Maintainability review", description="Review maintainability", type=TaskType.review, role="maintainability_reviewer", dependencies=["test"], read_paths=["codex_hive"], metadata={"confidence": 0.66}),
        ]
        lowered = mission.mission.lower()
        strategy = requested_strategy or "auto"
        if strategy == "auto":
            if "review" in lowered:
                strategy = "role-split-review"
            elif "flaky" in lowered or "bug" in lowered or "fix" in lowered:
                strategy = "competitive-generation"
                tasks.insert(
                    3,
                    TaskSpec(task_id="impl-alt", title="Alternative fix", description="Competing implementation", type=TaskType.bugfix, role="implementer", dependencies=["architect"], owned_paths=["codex_hive/runtime/generated_alt.py"], read_paths=["codex_hive"], write_enabled=True, metadata={"confidence": 0.74}),
                )
            else:
                strategy = "plan-then-execute-council"
        ownership = analyze_ownership(tasks)
        return PlannerOutput(mission=mission, tasks=tasks, strategy=strategy, ownership=ownership, notes=["v1 heuristic planner"])

    async def execute_plan(self, run_id: str, planner_output: PlannerOutput, dry_run: bool = False) -> RunReport:
        run_dir = self.repo_root / self.config.general.artifacts_dir / run_id
        artifact_writer = ArtifactWriter(run_dir)
        existing_run = self.db.get_run(run_id)
        resumed_statuses, resumed_results = self._load_resume_state(run_id)
        run_record = RunRecord(
            run_id=run_id,
            mission=planner_output.mission.mission,
            strategy=planner_output.strategy,
            status=RunStatus.running,
            created_at=existing_run.created_at if existing_run else datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            repo_root=str(self.repo_root),
            artifacts_dir=str(run_dir),
        )
        self.db.upsert_run(run_record)
        self.event_logger.append(
            EventRecord(
                event_type="plan_ready",
                run_id=run_id,
                payload={
                    "strategy": planner_output.strategy,
                    "tasks": [task.task_id for task in planner_output.tasks],
                },
            )
        )
        artifact_writer.write_report(
            RunReport(
                run_id=run_id,
                mission=planner_output.mission,
                status=RunStatus.running,
                strategy=planner_output.strategy,
                tasks=planner_output.tasks,
                worker_results=resumed_results,
            ),
            [],
            planner_output=planner_output,
            events=[],
        )
        if existing_run is None:
            self.event_logger.append(EventRecord(event_type="run_created", run_id=run_id, payload={"strategy": planner_output.strategy}))
        else:
            self.event_logger.append(EventRecord(event_type="run_resumed", run_id=run_id, payload={"strategy": planner_output.strategy}))
        for task in planner_output.tasks:
            payload = task.model_dump(mode="json")
            status = resumed_statuses.get(task.task_id, RunStatus.pending)
            if status == RunStatus.succeeded:
                for result in resumed_results:
                    if result.task_id == task.task_id:
                        payload = result.model_dump(mode="json")
                        break
            self.db.upsert_task(StoredTaskRecord(run_id=run_id, task_id=task.task_id, role=task.role, status=status, payload=payload))

        statuses = {task.task_id: resumed_statuses.get(task.task_id, RunStatus.pending) for task in planner_output.tasks}
        results: list[WorkerResult] = list(resumed_results)
        ordered = self.scheduler.order(planner_output.tasks, planner_output.ownership)
        while True:
            if self._is_cancelled(run_id):
                break
            ready = [task for task in ordered if statuses[task.task_id] in {RunStatus.pending, RunStatus.ready} and all(statuses.get(dep) == RunStatus.succeeded for dep in task.dependencies)]
            if not ready:
                break
            batches = self.scheduler.batch(ready, self.config.general.max_parallel_agents)
            for batch in batches:
                if self._is_cancelled(run_id):
                    break
                self.event_logger.append(
                    EventRecord(
                        event_type="batch_started",
                        run_id=run_id,
                        payload={"tasks": [task.task_id for task in batch]},
                    )
                )
                coroutines = [self._run_task(run_id, planner_output.mission, task, dry_run=dry_run) for task in batch]
                batch_results = await asyncio.gather(*coroutines, return_exceptions=True)
                for task, outcome in zip(batch, batch_results):
                    if isinstance(outcome, Exception):
                        statuses[task.task_id] = RunStatus.failed
                        self.db.upsert_task(StoredTaskRecord(run_id=run_id, task_id=task.task_id, role=task.role, status=RunStatus.failed, payload={"error": str(outcome)}))
                        self.event_logger.append(EventRecord(event_type="worker_failed", run_id=run_id, task_id=task.task_id, payload={"error": str(outcome)}))
                    else:
                        statuses[task.task_id] = RunStatus.succeeded if outcome.status == WorkerStatus.succeeded else RunStatus.failed
                        results.append(outcome)
                        self.db.upsert_task(StoredTaskRecord(run_id=run_id, task_id=task.task_id, role=task.role, status=statuses[task.task_id], payload=outcome.model_dump(mode="json")))
                        self.event_logger.append(EventRecord(event_type="worker_completed", run_id=run_id, task_id=task.task_id, payload={"status": outcome.status.value}))
                if self._is_cancelled(run_id):
                    break
                if any(status == RunStatus.failed for status in statuses.values()):
                    break
            if any(status == RunStatus.failed for status in statuses.values()):
                break

        review_findings = [finding for result in results for finding in result.findings]
        reliability_map = {result.agent_id: result.confidence for result in results}
        consensus = merge_findings(
            review_findings,
            total_agents=max(1, len([result for result in results if result.findings])),
            reliability_map=reliability_map,
            confirmed_threshold=self.config.consensus.confirmed_threshold,
            needs_verification_threshold=self.config.consensus.needs_verification_threshold,
        )
        self.event_logger.append(
            EventRecord(
                event_type="consensus_ready",
                run_id=run_id,
                payload={"finding_count": len(consensus.findings), "overall_score": consensus.overall_score},
            )
        )
        if planner_output.strategy in {"competitive-generation", "debate"} and len([item for item in results if item.role == "implementer"]) > 1:
            best = judge_best([item for item in results if item.role == "implementer"])
            consensus = apply_debate_round(consensus, f"Selected {best.task_id} as best candidate.")
            self.event_logger.append(
                EventRecord(
                    event_type="debate_applied",
                    run_id=run_id,
                    payload={"selected_task_id": best.task_id, "debate_rounds": consensus.debate_rounds},
                )
            )

        merge_plan = self.merger.plan(run_id, results)
        self.event_logger.append(
            EventRecord(
                event_type="merge_planned",
                run_id=run_id,
                payload={"branches": merge_plan.branch_order, "actions": merge_plan.merge_actions},
            )
        )
        async def _integrate():
            return self.merger.integrate([result for result in results if result.status == WorkerStatus.succeeded])
        merged_files = [] if self._is_cancelled(run_id) else await self.git_queue.run(_integrate)
        self.event_logger.append(
            EventRecord(
                event_type="merge_completed",
                run_id=run_id,
                payload={"merged_files": merged_files},
            )
        )
        verification_results = [] if self._is_cancelled(run_id) else await run_verification(self.repo_root, detect_commands(self.repo_root))
        self.event_logger.append(
            EventRecord(
                event_type="verification_completed",
                run_id=run_id,
                payload={
                    "commands": [item.command for item in verification_results],
                    "returncodes": [item.returncode for item in verification_results],
                },
            )
        )
        mission_check = self.mission_keeper.check(planner_output.mission, results)
        self.event_logger.append(
            EventRecord(
                event_type="mission_checked",
                run_id=run_id,
                payload=mission_check.model_dump(mode="json"),
            )
        )
        if self._is_cancelled(run_id):
            status = RunStatus.cancelled
        elif mission_check.passed and all(item_status == RunStatus.succeeded for item_status in statuses.values()):
            status = RunStatus.succeeded
        elif not mission_check.passed:
            status = RunStatus.escalated
        else:
            status = RunStatus.failed
        report = RunReport(
            run_id=run_id,
            mission=planner_output.mission,
            status=status,
            strategy=planner_output.strategy,
            completed_at=datetime.now(timezone.utc),
            tasks=planner_output.tasks,
            worker_results=results,
            consensus_report=consensus,
            merge_plan=merge_plan,
            mission_check=mission_check,
            final_summary=f"Merged {len(merged_files)} files. Mission check={'pass' if mission_check.passed else 'fail'}.",
        )
        artifact_writer.write_report(
            report,
            verification_results,
            planner_output=planner_output,
            events=self.event_logger.read_run(run_id),
        )
        self.db.upsert_run(
            RunRecord(
                run_id=run_id,
                mission=planner_output.mission.mission,
                strategy=planner_output.strategy,
                status=status,
                created_at=run_record.created_at,
                updated_at=datetime.now(timezone.utc),
                repo_root=str(self.repo_root),
                artifacts_dir=str(run_dir),
            )
        )
        self.event_logger.append(EventRecord(event_type="run_completed", run_id=run_id, payload={"status": status.value}))
        artifact_writer.write_report(
            report,
            verification_results,
            planner_output=planner_output,
            events=self.event_logger.read_run(run_id),
        )
        return report

    async def _run_task(self, run_id: str, mission: MissionSpec, task: TaskSpec, dry_run: bool = False) -> WorkerResult:
        agent_id = f"{task.role}-{uuid4().hex[:8]}"
        worktree_path = None
        branch_name = None
        if task.write_enabled:
            worktree_path, branch_name = self.worktrees.create(run_id, task.task_id, task.role)
        assignment = TaskAssignment(run_id=run_id, task=task, agent_id=agent_id, worktree_path=worktree_path, branch_name=branch_name)
        envelope = WorkerPromptEnvelope(
            assignment=assignment,
            mission=mission,
            role_instructions=ROLE_PROMPTS.get(task.role, "Return WorkerResult JSON."),
            context_files=task.read_paths,
        )
        self.db.upsert_execution(
            AgentExecutionRecord(
                run_id=run_id,
                task_id=task.task_id,
                agent_id=agent_id,
                role=task.role,
                status="running",
                adapter=self.adapter.name,
                worktree_path=worktree_path,
                branch_name=branch_name,
            )
        )
        self.event_logger.append(
            EventRecord(
                event_type="worker_started",
                run_id=run_id,
                task_id=task.task_id,
                payload={
                    "agent_id": agent_id,
                    "role": task.role,
                    "write_enabled": task.write_enabled,
                    "dependencies": task.dependencies,
                    "worktree_path": worktree_path,
                    "branch_name": branch_name,
                },
            )
        )
        if dry_run:
            result = WorkerResult(task_id=task.task_id, agent_id=agent_id, role=task.role, status=WorkerStatus.succeeded, summary="Dry run only", confidence=1.0, worktree_path=worktree_path, branch_name=branch_name)
        else:
            cwd = Path(worktree_path) if worktree_path else self.repo_root
            result = await self.dispatcher.dispatch(assignment, envelope, cwd)
        return result

    def _is_cancelled(self, run_id: str) -> bool:
        cancel_marker = self.repo_root / self.config.general.artifacts_dir / run_id / "cancelled"
        if cancel_marker.exists():
            return True
        record = self.db.get_run(run_id)
        return record is not None and record.status == RunStatus.cancelled

    def _load_resume_state(self, run_id: str) -> tuple[dict[str, RunStatus], list[WorkerResult]]:
        statuses: dict[str, RunStatus] = {}
        results: list[WorkerResult] = []
        for record in self.db.list_tasks(run_id):
            status = record.status
            if status in {RunStatus.failed, RunStatus.cancelled, RunStatus.blocked, RunStatus.retrying}:
                statuses[record.task_id] = RunStatus.pending
                continue
            statuses[record.task_id] = status
            if status == RunStatus.succeeded and "agent_id" in record.payload:
                results.append(WorkerResult.model_validate(record.payload))
        return statuses, results
