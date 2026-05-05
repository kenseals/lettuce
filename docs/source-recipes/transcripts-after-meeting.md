# Source Recipe: Transcripts / After Meetings

Use this recipe for Fathom, Granola, Zoom, Otter, Meet exports, transcript-summary emails, or operator-selected transcript files. The runtime owns transcript access, OAuth, browser sessions, exports, and any after-meeting trigger. Lettuce records the source contract and resulting events.

## Runtime Access Required

At least one of:

- transcript tool connector/API/MCP already available to the runtime;
- operator-exported transcript files or pasted transcript text;
- transcript notification emails with accessible links or summaries;
- operator-present browser access to the transcript tool;
- meeting artifacts in local files or a known folder.

Do not build a new transcript integration inside Lettuce during onboarding. If access is not already usable, record `needs_setup` and the smallest next setup action.

## Operator Questions

Ask one at a time, with context:

1. Which transcript tool or source should we start with? Examples: Fathom, Granola, Zoom, Otter, Meet export, transcript emails, or manual files.
2. Which calls are in scope? Examples: customer, product discovery, sales, support, internal strategy, partner, investor.
3. What should always be skipped? Examples: personal calls, recruiting, legal, medical, unrelated orgs, calls without consent.
4. What should trigger ingestion? Usually after meetings, operator-selected exports, or manual request.
5. What first tiny sample is safe? Usually 1-3 recent operator-approved calls.

## Classification

- `available_now`: runtime can inspect/export a tiny approved sample now.
- `needs_setup`: operator must export a file, connect OAuth/MCP/API, or open the transcript app.
- `defer`: useful later, but not needed for first setup.
- `manual-only`: operator will paste/export/share transcripts when they want Lettuce to process them.

## Source Record Command

Available now:

```bash
lettuce add-source transcript <repo-path> \
  --name meeting-transcripts \
  --workspace <tool-or-account-label> \
  --access-status available_now \
  --sample-policy "after-meeting or first-3-operator-approved transcripts before any backfill" \
  --privacy-notes "only org-scoped calls with consent/permission; skip personal/legal/recruiting/unrelated calls" \
  --setup-next-action "sample 1-3 operator-approved transcripts, then review output before recurring checks" \
  --commit
```

Needs setup:

```bash
lettuce add-source transcript <repo-path> \
  --name meeting-transcripts \
  --workspace <tool-or-account-label> \
  --access-status needs_setup \
  --sample-policy "operator exports or pastes one transcript before recurring access" \
  --privacy-notes "only org-scoped calls with consent/permission" \
  --setup-next-action "export/share one transcript or connect the existing transcript tool in the runtime" \
  --commit
```

Use provider-specific source types (`fathom`, `granola`, `zoom`) only when that label is useful. Generic `transcript` is fine for first setup.

## Privacy / Sample Defaults

- Start with 1-3 operator-approved transcripts.
- Preserve call title, timestamp, source tool, source URL/id, participants when safe, export path, and consent/availability basis.
- Redact or omit sensitive participant details when not needed.
- Do not ingest calls from unrelated orgs just because the runtime can access them.
- Do not infer recording consent; preserve the operator-provided basis.

## First Tiny Sample Path

If the runtime has a transcript file or pasted transcript:

```bash
lettuce add-event <repo-path> \
  --stream streams/inbox/transcripts \
  --title "<call title>" \
  --body-file /tmp/lettuce-transcript-sample.md \
  --source "transcript:<tool-or-export>" \
  --commit
lettuce run <repo-path> --stream streams/inbox/transcripts --review --commit
lettuce reviews <repo-path>
```

If handlers currently subscribe only to direct inbox events, the runtime may instead ingest a concise transcript brief through `ingest-direct` while preserving transcript provenance in the body. Label that as a bridge, not a real transcript connector.

## Verification Checks

- `sources/` contains a transcript source record with honest access status.
- The source record states trigger/cadence, sample policy, privacy boundary, and next setup action.
- Any sample event preserves transcript provenance.
- Review output is inspected before any recurring after-meeting check or backfill.
- The handoff says exactly when the runtime should check this source.

## Operator Handoff

Example:

> I recorded transcripts for `<org>` as `<available_now|needs_setup|defer>`. The intended trigger is `<after meetings|operator-selected export|manual only>`. I will only sample `<n>` org-scoped transcript(s) first, preserve source/consent details, and show review proposals before durable brain updates.
