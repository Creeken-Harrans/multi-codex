from .common import json_contract

PROMPT = f"List concrete findings with severity and evidence. No praise. {json_contract('WorkerResult')}"
