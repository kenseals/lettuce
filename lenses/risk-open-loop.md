---
id: risk_open_loop
name: Risk / Open Loop Lens
applies_to:
  - message
  - transcript
  - email
  - note
  - session_summary
fit_boosts:
  - risk
  - concern
  - unclear
  - blocker
  - don't
  - do not
  - avoid
  - validate
  - approval
  - evidence
route_hints:
  - project_artifact
  - daily_memory
  - followup_candidate
---

# Risk / Open Loop Lens

## Role

Detect unresolved questions, boundaries, blockers, approval needs, validation gaps, and evidence warnings before the agent acts.

## Good outputs

- surfaces the actual uncertainty or boundary
- distinguishes a real blocker from normal ambiguity
- identifies validation gates before build recommendations
- records caveats such as saved external post vs fresh instruction
- routes to preview/follow-up instead of pretending the loop is closed

## Bad outputs

- invents risks to sound cautious
- blocks low-risk internal work unnecessarily
