from .common import json_contract

PROMPT = f"Integrate accepted changes safely, report conflicts and required verification. {json_contract('WorkerResult')}"
