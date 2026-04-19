"""Artifact writing."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import ArtifactIndex, EventRecord, PlannerOutput, RunReport
from ..utils.paths import ensure_dir
from ..utils.serialization import write_json
from .renderers import render_final_report, render_summary


class ArtifactWriter:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = ensure_dir(run_dir)
        self.tasks_dir = ensure_dir(self.run_dir / "tasks")
        self.agents_dir = ensure_dir(self.run_dir / "agents")
        self.raw_dir = ensure_dir(self.run_dir / "raw")

    def write_report(
        self,
        report: RunReport,
        verification_results,
        planner_output: PlannerOutput | None = None,
        events: list[EventRecord] | None = None,
    ) -> ArtifactIndex:
        files: list[str] = []
        write_json(self.run_dir / "run.json", report.model_dump(mode="json"))
        files.append("run.json")
        write_json(self.run_dir / "mission.json", report.mission.model_dump(mode="json"))
        files.append("mission.json")
        if planner_output is not None:
            write_json(self.run_dir / "plan.json", planner_output.model_dump(mode="json"))
            files.append("plan.json")
        if report.consensus_report:
            write_json(self.run_dir / "consensus.json", report.consensus_report.model_dump(mode="json"))
            files.append("consensus.json")
        if report.merge_plan:
            write_json(self.run_dir / "merge-plan.json", report.merge_plan.model_dump(mode="json"))
            files.append("merge-plan.json")
        if report.mission_check:
            write_json(self.run_dir / "mission-check.json", report.mission_check.model_dump(mode="json"))
            files.append("mission-check.json")
        summary = render_summary(report)
        (self.run_dir / "summary.md").write_text(summary, encoding="utf-8")
        files.append("summary.md")
        final_report = render_final_report(report, verification_results)
        (self.run_dir / "final-report.md").write_text(final_report, encoding="utf-8")
        files.append("final-report.md")
        if events is not None:
            events_path = self.run_dir / "events.jsonl"
            with events_path.open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
            files.append("events.jsonl")
        for result in report.worker_results:
            write_json(self.tasks_dir / f"{result.task_id}.json", result.model_dump(mode="json"))
            files.append(f"tasks/{result.task_id}.json")
            files.extend(self._write_worker_trace(result))
        return ArtifactIndex(run_dir=str(self.run_dir), files=files)

    def _write_worker_trace(self, result) -> list[str]:
        trace = result.metadata.get("trace") if isinstance(result.metadata, dict) else None
        if not trace:
            return []
        trace_dir = ensure_dir(self.agents_dir / f"{result.task_id}--{result.agent_id}")
        files: list[str] = []
        write_json(trace_dir / "input-envelope.json", trace.get("input_envelope", {}))
        files.append(f"agents/{trace_dir.name}/input-envelope.json")
        write_json(trace_dir / "result.json", result.model_dump(mode="json"))
        files.append(f"agents/{trace_dir.name}/result.json")
        write_json(trace_dir / "trace.json", trace)
        files.append(f"agents/{trace_dir.name}/trace.json")
        command = trace.get("command")
        if command:
            (trace_dir / "command.txt").write_text(" ".join(command), encoding="utf-8")
            files.append(f"agents/{trace_dir.name}/command.txt")
        if trace.get("prompt") is not None:
            (trace_dir / "prompt.txt").write_text(str(trace.get("prompt")), encoding="utf-8")
            files.append(f"agents/{trace_dir.name}/prompt.txt")
        if trace.get("stdout") is not None:
            (trace_dir / "stdout.txt").write_text(str(trace.get("stdout")), encoding="utf-8")
            files.append(f"agents/{trace_dir.name}/stdout.txt")
        if trace.get("stderr") is not None:
            (trace_dir / "stderr.txt").write_text(str(trace.get("stderr")), encoding="utf-8")
            files.append(f"agents/{trace_dir.name}/stderr.txt")
        return files
