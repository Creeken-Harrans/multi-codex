"""Artifact-facing schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TaskArtifact(BaseModel):
    task_id: str
    files: list[str] = Field(default_factory=list)


class AgentArtifact(BaseModel):
    agent_id: str
    files: list[str] = Field(default_factory=list)
