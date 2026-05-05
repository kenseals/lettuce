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
- `transcripts-after-meeting.md`: transcript setup for Fathom/Granola/Zoom/Otter/exports with after-meeting or operator-selected triggers.
- `work-systems-github-linear.md`: GitHub, Linear, docs, Notion, and Slack work-system setup with scoped samples and honest access status.

## Onboarding Use

During first setup, the agent should not ask a generic source question and then improvise. Use recipes as the source setup engine:

1. Identify candidate source classes with the operator.
2. Load the relevant recipe before asking source-specific questions.
3. Explain what the source can contribute and what the runtime, not Lettuce, must own.
4. Ask the recipe's operator questions one at a time.
5. Classify the source honestly.
6. Write a source record using the recipe's command shape.
7. If possible, run the recipe's first tiny sample path.
8. Run the recipe's verification checks.
9. Hand off the result using the recipe's handoff language.

If the runtime cannot actually inspect a source yet, do not describe it as connected. Record `needs_setup`, `defer`, or manual-only posture and tell the operator the smallest next action.

## Freshness Mode Hints

When a source recipe records trigger/cadence intent, keep it legible enough that `lettuce status` can summarize the repo's maintenance posture:

- `manual`: operator-triggered only.
- `after-meeting`: check when a transcript or meeting artifact lands.
- `daily`: runtime or cron should run a daily check.
- `source-check`: source is available now, but no stronger cadence was recorded yet.
- `subscription-pull`: runtime should eventually mirror a configured shared stream; today this mode records intended maintenance only.

The runtime still owns the actual scheduler or connector. Lettuce owns the durable source/subscription contract and the resulting checkpoints, reviews, logs, and git history.
