# Prompts

Each role uses short, strict instructions:

- planner: task DAG, risk, owned paths, strategy
- scout: read-only exploration
- architect: interfaces and boundaries
- implementer: assigned slice only, honest assumptions and tests
- tester: focused verification and failure evidence
- reviewers: findings only, with severity and evidence
- judge: blind candidate comparison
- mission keeper: drift and acceptance coverage only

All roles are expected to return structured JSON contracts.
