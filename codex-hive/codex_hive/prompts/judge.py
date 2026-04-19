from .common import json_contract

PROMPT = f"Blindly compare candidates, justify the best or synthesize a merged answer. {json_contract('WorkerResult')}"
