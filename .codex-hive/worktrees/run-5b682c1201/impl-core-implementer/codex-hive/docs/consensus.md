# Consensus

Consensus is not majority vote. Findings are deduplicated using a canonical key derived from normalized title and description.

For each merged finding:

- `agreement_ratio = supporting_agents / total_agents`
- `base = agreement_ratio * max_confidence`
- `evidence_factor = min(1.0, evidence_count / 3)`
- `reliability_factor = mean(agent_reliability)`
- `consensus_score = base * (0.6 + 0.2 * evidence_factor + 0.2 * reliability_factor)`

Levels:

- `confirmed` if score >= configured confirmed threshold
- `needs_verification` if score >= configured verification threshold
- `unverified` otherwise

Debate rounds can nudge scores upward after a judge or challenge phase adds stronger evidence.
