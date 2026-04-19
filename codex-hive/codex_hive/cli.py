"""CLI entrypoint."""

from __future__ import annotations

import asyncio
import json
import shutil
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
    plan_output = orchestrator.plan(mission, strategy)
    report = asyncio.run(orchestrator.execute_plan(orchestrator.create_run_id(task), plan_output, dry_run=dry_run))
    payload = report.model_dump(mode="json")
    if json_output:
        render_json(payload)
        return
    console.print(f"Run {report.run_id}: {report.status.value}")
    console.print(f"Artifacts: {root / config.general.artifacts_dir / report.run_id}")


@app.command()
def status(
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    root = resolve_repo_root(repo_root)
    _, db, _ = load_app(root)
    runs = db.list_runs()
    if json_output:
        render_json([item.model_dump(mode="json") for item in runs])
        return
    table = Table("Run ID", "Status", "Strategy", "Mission")
    for item in runs:
        table.add_row(item.run_id, item.status.value, item.strategy, item.mission)
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
    orchestrator = Orchestrator(root, config, db, eventlog, pick_adapter(config, adapter))
    report = asyncio.run(orchestrator.execute_plan(run_id, orchestrator.plan(orchestrator.parse_mission(run_record.mission), run_record.strategy)))
    console.print(f"Resumed {report.run_id}: {report.status.value}")


@app.command()
def cancel(
    run_id: str,
    repo_root: Annotated[Path | None, typer.Option("--repo-root")] = None,
) -> None:
    root = resolve_repo_root(repo_root)
    _, db, _ = load_app(root)
    record = db.get_run(run_id)
    if record is None:
        raise typer.BadParameter(f"Unknown run: {run_id}")
    record.status = RunStatus.cancelled
    db.upsert_run(record)
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
