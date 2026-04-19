from .common import json_contract

PROMPT = f"Produce a DAG, risks, owned_paths, and strategy. {json_contract('PlannerOutput')}"
