from .common import json_contract

PROMPT = (
    "Review the orchestrator-provided mission plan instead of creating a new DAG. "
    "Check whether dependencies, owned paths, role split, risks, and acceptance criteria look coherent. "
    "Do not re-plan the whole project. Do not inspect unrelated parent repositories unless needed. "
    f"{json_contract('WorkerResult')}"
)
