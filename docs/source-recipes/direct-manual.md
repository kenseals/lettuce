# Source Recipe: Direct / Manual

Use this recipe for operator-forwarded, pasted, dictated, or otherwise explicitly handed-off work signal. This is the baseline source every normal first setup should support.

## Runtime Access Required

- Access to the current conversation surface, CLI, or local temp files.
- Permission to write a temporary markdown body file when the signal is longer than a sentence.
- Permission to run `lettuce ingest-direct`, `lettuce add-source direct`, `lettuce run`, and optional review commands.

Do not build a duplicate chat bot, browser surface, or intake form inside Lettuce. The runtime already owns the intake surface.

## Operator Questions

- Which org-scoped Lettuce repo should this signal belong to?
- What phrase should trigger durable capture, for example: "run Lettuce on this"?
- Should onboarding and sensitive follow-ups use review mode before `brain/*` updates land?
- What should always be skipped: personal, family, legal, medical, recruiting, or other out-of-scope content?

## Connection Plan

Manual/direct is the baseline connection plan. It requires no API, MCP, webhook, or cron.

- Trigger: operator explicitly forwards, pastes, dictates, exports, or points at a signal.
- Access method: current agent conversation, temporary file, or local shell-controlled input.
- Scheduling: none unless a later runtime task chooses to periodically ask for/manual-review signal.
- Fallback: if another source is not connected yet, use this recipe to ingest one selected item with provenance.

Do not turn manual/direct into background polling. If the source becomes recurring, add a separate source record using the appropriate recipe.

## Classification

- `manual-only`
- Persist as `access_status: available_now` when the runtime can accept manual input now.
- Use the source record text and `sample_policy` to say the source is operator-triggered, not polled.

## Source Record Command

```bash
lettuce add-source direct <repo-path> \
  --name manual-direct \
  --access-status available_now \
  --sample-policy "manual-only: operator-forwarded-or-pasted-signals via runtime trigger phrase" \
  --privacy-notes "skip personal, family, legal, medical, recruiting, and unrelated org content" \
  --setup-next-action "operator can say 'run Lettuce on this' when a scoped work signal should become durable" \
  --commit
```

## Privacy / Sample Defaults

- Default to one operator-approved signal at a time.
- Preserve source surface, sender/operator, consent basis, and message/chat/thread ids when available.
- Keep the operator's wording intact for the first sample; prefer `--body-file` over shell-escaped inline text.
- Skip content that belongs in personal memory or a different org-scoped Lettuce.

## First Tiny Sample Path

1. Write the operator-approved signal to a temporary markdown file.
2. Ingest it as direct input with provenance.
3. Run handlers behind review unless the operator explicitly asked to bypass review.

```bash
lettuce ingest-direct <repo-path> \
  --title "<short signal title>" \
  --body-file /tmp/lettuce-direct-sample.md \
  --source <agent.surface> \
  --surface <surface> \
  --sender <operator> \
  --consent operator-direct-request \
  --commit
lettuce run <repo-path> --review --commit
lettuce reviews <repo-path>
```

## Verification Checks

- `sources/` contains the direct/manual source record and it clearly states the manual-only trigger behavior.
- `streams/inbox/direct/` contains the sampled event with provenance.
- Review mode created pending proposals or a clear skip reason.
- No durable `brain/*` update landed before approval when review mode was requested.
- The handoff explains that this source is operator-triggered, not scheduled.

## Operator Handoff

Example:

> Manual/direct Lettuce capture is ready for `<org>` at `<repo-path>`. When you say "run Lettuce on this," I will write the signal with provenance, run the handlers, and show review proposals before durable brain updates. This source is manual-only for now; no polling or background inbox checks were configured.
