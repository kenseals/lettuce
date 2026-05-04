# Lettuce Source Recipes

These files are agent-readable source setup recipes for Lettuce onboarding and ongoing source configuration.

Use them after `docs/source-discovery-recipes.md` tells you which source class matters. Each recipe keeps the runtime boundary explicit:

- the runtime owns chat, email, browser, OAuth, connectors, exports, and schedules;
- Lettuce owns source records, stream events, provenance, review artifacts, checkpoints, and git history.

## Recipe Pattern

Every recipe should answer the same questions in the same order:

1. `Runtime access required`: what the agent runtime must already own or obtain outside Lettuce.
2. `Operator questions`: the minimum questions needed before recording source intent.
3. `Classification`: whether the source is `available_now`, `needs_setup`, `defer`, or `manual-only`.
4. `Source record command`: the `lettuce add-source ...` command that records the durable contract.
5. `Privacy/sample defaults`: small-sample and redaction defaults before any backfill.
6. `First tiny sample path`: the smallest safe path to prove the source is useful.
7. `Verification checks`: what to inspect after setup or sampling.
8. `Operator handoff`: how to summarize the result and next trigger.

## Classification Rule

`manual-only` is an agent-readable recipe posture, not a CLI `access_status` enum. When a source is manual-only:

- the runtime can ingest it only when the operator forwards, pastes, exports, or explicitly points to it;
- the source record should still be created so future agent behavior is inspectable;
- the persisted `access_status` should stay truthful to the current CLI, usually `available_now` for manual/direct sources the runtime can accept now, or `unknown` if even that boundary is not settled yet;
- the manual-only behavior should be stated in `sample_policy`, `privacy_notes`, or the body of the source record.

## Concrete Recipes

- `direct-manual.md`: baseline recipe every first setup should support.
- `email-recurring.md`: recurring-ish email recipe that still starts sample-first and runtime-owned.
