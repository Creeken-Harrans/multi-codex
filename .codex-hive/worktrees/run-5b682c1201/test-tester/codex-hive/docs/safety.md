# Safety

Safety defaults:

- write-heavy tasks are isolated
- reviewer roles are read-only
- merge-like operations are serialized through a lock-backed queue
- mission drift is checked before final success
- verification is explicit and skip reasons are recorded

Failure classes:

- Retryable: timeouts, transient subprocess failures
- Non-retryable: missing binary, invalid config, unresolved merge conflict needing human input

If the mission guard fails, the run ends in `escalated`.
