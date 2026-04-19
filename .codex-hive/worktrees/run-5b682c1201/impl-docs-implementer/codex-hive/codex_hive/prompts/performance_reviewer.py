from .common import json_contract

PROMPT = f"Focus on complexity, IO amplification, hot paths, caching, and regressions. {json_contract('WorkerResult')}"
