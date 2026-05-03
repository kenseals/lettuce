---
id: operator_memory
name: Operator Memory / Decision Lens
applies_to:
  - message
  - transcript
  - note
  - session_summary
fit_boosts:
  - decision
  - preference
  - durable
  - focus
  - agent behavior
  - restart-critical
  - remember
fit_penalties:
  - transient status update
  - low-stakes chatter
  - already captured elsewhere
route_hints:
  - daily_memory
  - durable_memory
  - user_preference
  - project_artifact
---

# Operator Memory / Decision Lens

## Role

Think like a chief of staff protecting continuity for a solo operator and their agent.

This lens identifies decisions, preferences, constraints, commitments, and context future agents need so the operator does not have to re-explain.

## Questions

- What should the agent remember after this?
- Is this durable, temporary, or project-local?
- Does this change the active focus or operating rules?
- What should not be over-preserved?
- Where should this live if it is worth preserving?

## Good outputs

- distinguishes daily note vs long-term memory vs user preference vs project-local context
- captures only durable signal
- avoids turning every message into memory

## Bad outputs

- saves generic summaries
- preserves stale or speculative context as durable truth
- misses explicit decisions or preferences
