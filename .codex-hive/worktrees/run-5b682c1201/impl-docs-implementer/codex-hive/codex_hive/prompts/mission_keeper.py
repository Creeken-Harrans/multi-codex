from .common import json_contract

PROMPT = f"Preserve user intent, reject drift, report scope violations. {json_contract('MissionCheckResult')}"
