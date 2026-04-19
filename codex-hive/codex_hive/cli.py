"""CLI entrypoint."""

from __future__ import annotations

import asyncio
import json
import shutil
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .adapters.codex_cli import CodexCLIAdapter
from .adapters.fake_agent import FakeAgentAdapter
from .config import AppConfig, DEFAULT_CONFIG_TEXT
from .constants import DEFAULT_CONFIG_FILENAME, DEFAULT_DB_NAME, DEFAULT_EVENT_LOG
from .db import StateDB
from .eventlog import EventLogger
from .models import RepoHealth, RunReport, RunStatus
from .runtime.orchestrator import Orchestrator
from .runtime.adaptive_planner import plan_with_codex, should_use_adaptive_planner
from .runtime.resume import ResumeManager
from .utils.paths import ensure_dir, resolve_repo_root
from .utils.serialization import to_json, write_json

app = typer.Typer(help="codex-hive orchestration CLI", no_args_is_help=True)
console = Console()


def load_app(repo_root: Path) -> tuple[AppConfig, StateDB, EventLogger]:
    config = AppConfig.from_path(repo_root / DEFAULT_CONFIG_FILENAME)
    state_dir = ensure_dir(repo_root / ".codex-hive")
    db = StateDB(state_dir / DEFAULT_DB_NAME)
    eventlog = EventLogger(state_dir / DEFAULT_EVENT_LOG)
    return config, db, eventlog


def pick_adapter(config: AppConfig, adapter_name: str):
    if adapter_name == "codex":
        return CodexCLIAdapter(config)
    return FakeAgentAdapter()


def render_json(data) -> None:
    console.print_json(to_json(data))


def summarize_tasks(db: StateDB, run_id: str) -> dict:
    tasks = db.list_tasks(run_id)
    counts = Counter(item.status.value for item in tasks)
    active = [f"{item.task_id}:{item.status.value}" for item in tasks if item.status in {RunStatus.running, RunStatus.retrying, RunStatus.awaiting_merge, RunStatus.blocked}]
    completed = counts.get(RunStatus.succeeded.value, 0)
    total = len(tasks)
    return {
        "total": total,
        "completed": completed,
        "counts": dict(sorted(counts.items())),
        "active": active,
    }


def print_run_progress(db: StateDB, run_id: str) -> None:
    run = db.get_run(run_id)
    if run is None:
        console.print(f"Unknown run: {run_id}")
        return
    summary = summarize_tasks(db, run_id)
    console.print(
        f"[{run.run_id}] {run.status.value} | completed {summary['completed']}/{summary['total']}"
    )
    if summary["counts"]:
        counts = ", ".join(f"{key}={value}" for key, value in summary["counts"].items())
        console.print(f"Task counts: {counts}")
    if summary["active"]:
        console.print(f"Active: {', '.join(summary['active'])}")


def format_event_message(event: dict) -> str | None:
    event_type = event.get("event_type")
    task_id = event.get("task_id")
    payload = event.get("payload", {})
    if event_type == "plan_ready":
        return f"[ORCHESTRATOR] Plan ready | strategy={payload.get('strategy')} | tasks={', '.join(payload.get('tasks', []))}"
    if event_type == "batch_started":
        return f"[HANDOFF] Dispatch batch -> {', '.join(payload.get('tasks', []))}"
    if event_type == "worker_started":
        suffix = f" role={payload.get('role')}"
        if payload.get("worktree_path"):
            suffix += f" worktree={payload.get('worktree_path')}"
        return f"[WORKER] Started {task_id}{suffix}"
    if event_type == "worker_completed":
        return f"[WORKER] Completed {task_id} | status={payload.get('status')}"
    if event_type == "worker_failed":
        return f"[WORKER] Failed {task_id} | error={payload.get('error')}"
    if event_type == "consensus_ready":
        return f"[CONSENSUS] Ready | findings={payload.get('finding_count')} | score={payload.get('overall_score')}"
    if event_type == "debate_applied":
        return f"[DEBATE] Applied | selected={payload.get('selected_task_id')} | rounds={payload.get('debate_rounds')}"
    if event_type == "merge_planned":
        return f"[MERGE] Planned | branches={len(payload.get('branches', []))} | actions={len(payload.get('actions', []))}"
    if event_type == "merge_completed":
        return f"[MERGE] Completed | files={', '.join(payload.get('merged_files', [])) or 'none'}"
    if event_type == "verification_completed":
        return f"[VERIFY] Completed | returncodes={payload.get('returncodes', [])}"
    if event_type == "mission_checked":
        return f"[MISSION] Checked | passed={payload.get('passed')} | score={payload.get('goal_alignment_score')}"
    if event_type == "run_completed":
        return f"[ORCHESTRATOR] Run completed | status={payload.get('status')}"
    return None


def start_progress_reporter(db_path: Path, eventlog_path: Path, run_id: str) -> tuple[threading.Event, threading.Thread]:
    stop_event = threading.Event()

    def worker() -> None:
        db = StateDB(db_path)
        seen_events = 0
        last_snapshot: tuple | None = None
        try:
            while not stop_event.is_set():
                if eventlog_path.exists():
                    lines = [line for line in eventlog_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                    for line in lines[seen_events:]:
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if event.get("run_id") != run_id:
                            continue
                        message = format_event_message(event)
                        if message:
                            console.print(f"[{run_id}] {message}")
                    seen_events = len(lines)
                run = db.get_run(run_id)
                if run is not None:
                    summary = summarize_tasks(db, run_id)
                    snapshot = (
                        run.status.value,
                        summary["completed"],
                        summary["total"],
                        tuple(summary["active"]),
                        tuple(sorted(summary["counts"].items())),
                    )
                    if snapshot != last_snapshot:
                        counts = ", ".join(f"{key}={value}" for key, value in summary["counts"].items()) or "no tasks yet"
                        line = f"[{run_id}] [PROGRESS] {run.status.value} | completed {summary['completed']}/{summary['total']} | {counts}"
                        if summary["active"]:
                            line += f" | active: {', '.join(summary['active'])}"
                        console.print(line)
                        last_snapshot = snapshot
                    if run.status in {RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled, RunStatus.escalated}:
                        break
                time.sleep(1.0)
        finally:
            db.connection.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return stop_event, thread


@app.command()
def init(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    ensure_dir(root / ".codex-hive" / "runs")
    ensure_dir(root / ".codex-hive" / "worktrees")
    config_path = root / DEFAULT_CONFIG_FILENAME
    if force or not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG_TEXT + "\n", encoding="utf-8")
    data = {"repo_root": str(root), "config_path": str(config_path), "initialized": True}
    if json_output:
        render_json(data)
        return
    console.print(f"Initialized codex-hive in {root}")


@app.command()
def plan(
    task: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    strategy: Annotated[str | None, typer.Option("--strategy")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    config, db, eventlog = load_app(root)
    orchestrator = Orchestrator(root, config, db, eventlog, FakeAgentAdapter())
    planner_output = orchestrator.plan(orchestrator.parse_mission(task), strategy)
    payload = planner_output.model_dump(mode="json")
    if json_output:
        render_json(payload)
        return
    console.print_json(to_json(payload))


@app.command()
def run(
    task: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    adapter: Annotated[str, typer.Option("--adapter")] = "fake",
    strategy: Annotated[str | None, typer.Option("--strategy")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    max_agents: Annotated[int | None, typer.Option("--max-agents")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    config, db, eventlog = load_app(root)
    if max_agents:
        config.general.max_parallel_agents = max_agents
    chosen_adapter = pick_adapter(config, adapter)
    orchestrator = Orchestrator(root, config, db, eventlog, chosen_adapter)
    mission = orchestrator.parse_mission(task)
    if chosen_adapter.name == "codex-cli" and (strategy is None or strategy == "auto") and should_use_adaptive_planner(mission):
        plan_output = asyncio.run(plan_with_codex(root, config, mission)) or orchestrator.plan(mission, strategy)
    else:
        plan_output = orchestrator.plan(mission, strategy)
    run_id = orchestrator.create_run_id(task)
    stop_event = None
    reporter_thread = None
    if not json_output:
        console.print(f"Starting run {run_id}")
        console.print(f"Strategy: {plan_output.strategy}")
        console.print(f"Tasks: {', '.join(item.task_id for item in plan_output.tasks)}")
        stop_event, reporter_thread = start_progress_reporter(db.path, eventlog.path, run_id)
    try:
        report = asyncio.run(orchestrator.execute_plan(run_id, plan_output, dry_run=dry_run))
    finally:
        if stop_event is not None and reporter_thread is not None:
            stop_event.set()
            reporter_thread.join(timeout=2)
    payload = report.model_dump(mode="json")
    if json_output:
        render_json(payload)
        return
    console.print(f"Run {report.run_id}: {report.status.value}")
    console.print(f"Artifacts: {root / config.general.artifacts_dir / report.run_id}")


@app.command()
def status(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    run_id: Annotated[str | None, typer.Option("--run-id")] = None,
    tasks: Annotated[bool, typer.Option("--tasks")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    _, db, _ = load_app(root)
    if run_id is not None:
        record = db.get_run(run_id)
        if record is None:
            raise typer.BadParameter(f"Unknown run: {run_id}")
        task_rows = db.list_tasks(run_id)
        if json_output:
            payload = {
                "run": record.model_dump(mode="json"),
                "tasks": [item.model_dump(mode="json") for item in task_rows],
                "summary": summarize_tasks(db, run_id),
            }
            render_json(payload)
            return
        print_run_progress(db, run_id)
        table = Table("Task ID", "Role", "Status")
        for item in task_rows:
            table.add_row(item.task_id, item.role, item.status.value)
        console.print(table)
        return
    runs = db.list_runs()
    if json_output:
        render_json([item.model_dump(mode="json") for item in runs])
        return
    table = Table("Run ID", "Status", "Strategy", "Mission", "Progress")
    for item in runs:
        progress = "-"
        if tasks:
            summary = summarize_tasks(db, item.run_id)
            progress = f"{summary['completed']}/{summary['total']}"
            if summary["active"]:
                progress += f" active={','.join(summary['active'])}"
        table.add_row(item.run_id, item.status.value, item.strategy, item.mission, progress)
    console.print(table)


@app.command()
def inspect(
    run_id: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    config, _, _ = load_app(root)
    run_file = root / config.general.artifacts_dir / run_id / "run.json"
    if not run_file.exists():
        raise typer.BadParameter(f"Unknown run: {run_id}")
    data = json.loads(run_file.read_text(encoding="utf-8"))
    if json_output:
        render_json(data)
        return
    console.print_json(to_json(data))


@app.command()
def trace(
    run_id: str,
    task_id: Annotated[str | None, typer.Option("--task-id")] = None,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    config, _, _ = load_app(root)
    agents_dir = root / config.general.artifacts_dir / run_id / "agents"
    if not agents_dir.exists():
        raise typer.BadParameter(f"No worker traces for {run_id}")
    trace_dirs = sorted(path for path in agents_dir.iterdir() if path.is_dir())
    if task_id is not None:
        trace_dirs = [path for path in trace_dirs if path.name.startswith(f"{task_id}--")]
    payload = []
    for trace_dir in trace_dirs:
        trace_file = trace_dir / "trace.json"
        result_file = trace_dir / "result.json"
        payload.append(
            {
                "trace_id": trace_dir.name,
                "trace": json.loads(trace_file.read_text(encoding="utf-8")) if trace_file.exists() else {},
                "result": json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else {},
            }
        )
    if json_output:
        render_json(payload)
        return
    for item in payload:
        trace_data = item["trace"]
        console.rule(item["trace_id"])
        console.print(f"cwd: {trace_data.get('cwd')}")
        console.print(f"command: {' '.join(trace_data.get('command', []))}")
        console.print("input:")
        console.print_json(to_json(trace_data.get("input_envelope", {})))
        if trace_data.get("final_message"):
            console.print("final_message:")
            console.print(trace_data["final_message"])
        else:
            console.print("reply/result:")
            console.print_json(to_json(item.get("result", {})))


@app.command()
def resume(
    run_id: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    adapter: Annotated[str, typer.Option("--adapter")] = "fake",
) -> None:
    root = resolve_repo_root(repo_root)
    config, db, eventlog = load_app(root)
    run_record = db.get_run(run_id)
    if run_record is None:
        raise typer.BadParameter(f"Unknown run: {run_id}")
    resumable_ids = {item.run_id for item in ResumeManager(db).resumable_runs()}
    if run_id not in resumable_ids:
        raise typer.BadParameter(f"Run is not resumable: {run_id}")
    orchestrator = Orchestrator(root, config, db, eventlog, pick_adapter(config, adapter))
    report = asyncio.run(orchestrator.execute_plan(run_id, orchestrator.plan(orchestrator.parse_mission(run_record.mission), run_record.strategy)))
    console.print(f"Resumed {report.run_id}: {report.status.value}")


@app.command()
def cancel(
    run_id: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    root = resolve_repo_root(repo_root)
    config, db, _ = load_app(root)
    record = db.get_run(run_id)
    if record is None:
        raise typer.BadParameter(f"Unknown run: {run_id}")
    record.status = RunStatus.cancelled
    db.upsert_run(record)
    run_dir = root / config.general.artifacts_dir / run_id
    ensure_dir(run_dir).joinpath("cancelled").write_text("cancelled\n", encoding="utf-8")
    console.print(f"Cancelled {run_id}")


@app.command()
def merge(
    run_id: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    root = resolve_repo_root(repo_root)
    config, _, _ = load_app(root)
    merge_plan_path = root / config.general.artifacts_dir / run_id / "merge-plan.json"
    if not merge_plan_path.exists():
        raise typer.BadParameter(f"No merge plan for {run_id}")
    run_path = root / config.general.artifacts_dir / run_id / "run.json"
    if run_path.exists():
        report = RunReport.model_validate_json(run_path.read_text(encoding="utf-8"))
        console.print(f"Run {run_id}: {report.status.value}")
    console.print(merge_plan_path.read_text(encoding="utf-8"))


@app.command()
def clean(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    root = resolve_repo_root(repo_root)
    state_dir = root / ".codex-hive"
    shutil.rmtree(state_dir, ignore_errors=True)
    console.print(f"Removed {state_dir}")


@app.command()
def doctor(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    health = RepoHealth(
        repo_root=str(root),
        git_available=shutil.which("git") is not None,
        codex_available=shutil.which("codex") is not None,
        config_found=(root / DEFAULT_CONFIG_FILENAME).exists(),
        writable_state_dir=ensure_dir(root / ".codex-hive").exists(),
    )
    if json_output:
        render_json(health.model_dump(mode="json"))
        return
    console.print_json(to_json(health.model_dump(mode="json")))


agents_app = typer.Typer(help="Manage agent profiles")
app.add_typer(agents_app, name="agents")


@agents_app.command("list")
def agents_list(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    config, _, _ = load_app(root)
    payload = [profile.model_dump(mode="json") for profile in config.agents.values()]
    if json_output:
        render_json(payload)
        return
    table = Table("Name", "Role", "Model", "Read-only")
    for profile in config.agents.values():
        table.add_row(profile.name, profile.role, profile.model, str(profile.read_only))
    console.print(table)


config_app = typer.Typer(help="Inspect configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    config, _, _ = load_app(root)
    payload = config.model_dump(mode="json")
    if json_output:
        render_json(payload)
        return
    console.print_json(to_json(payload))


@app.command("export-report")
def export_report(
    run_id: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    root = resolve_repo_root(repo_root)
    config, _, _ = load_app(root)
    run_dir = root / config.general.artifacts_dir / run_id
    run_json = run_dir / "run.json"
    if not run_json.exists():
        raise typer.BadParameter(f"Unknown run: {run_id}")
    report = RunReport.model_validate_json(run_json.read_text(encoding="utf-8"))
    target = output or (run_dir / "exported-report.json")
    write_json(target, report.model_dump(mode="json"))
    console.print(f"Exported report to {target}")


@app.command()
def review(
    task: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    run(task, repo_root=repo_root, strategy="role-split-review")


@app.command()
def debate(
    task: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    run(task, repo_root=repo_root, strategy="debate")


@app.command()
def judge(
    task: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    run(task, repo_root=repo_root, strategy="competitive-generation")


@app.command()
def benchmark(
    task: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    run(task, repo_root=repo_root, strategy="map-reduce", dry_run=True)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
