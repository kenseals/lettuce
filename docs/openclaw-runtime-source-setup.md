# OpenClaw Runtime Source Setup Contract

Lettuce does not own chat, inboxes, OAuth, browser sessions, MCP servers, or polling infrastructure. OpenClaw, or whatever agent runtime is operating Lettuce, owns those surfaces.

Lettuce's job is to give the runtime a durable protocol for turning agent-observed work signal into org-scoped context:

1. discover what signal source is available;
2. record the source intent and access boundary;
3. ingest a small operator-approved sample into a stream;
4. run handlers;
5. write useful brain updates with provenance and git history;
6. only then decide whether recurring polling or deeper setup is worth it.

Optional review mode exists for calibration, sensitive sources, high-impact updates, or explicit operator approval gates. It is not the normal product loop.

## Source setup loop

### 1. Anchor the organization

Every source belongs to one `(operator, org)` Lettuce repo. Before connecting a source, the agent should know:

- org slug/name;
- operator handle/name;
- repo path or repo URL;
- why this source belongs to this org rather than personal/general memory.

If that is unclear, ask before ingesting.

### 2. Inspect runtime access first

Before asking the operator to create anything new, the agent checks what it already has:

- current conversation surface: Telegram, iMessage, Discord, CLI, browser chat;
- file access: exported markdown, txt, eml, mbox, transcript files;
- configured tools/connectors: email, GitHub, Linear, calendar, browser, MCP;
- existing authenticated browser sessions;
- existing cron/scheduler capability.

Prefer the lowest-friction first sample. Do not create a new bot, webhook, OAuth app, or polling job just to prove source value.

### 3. Record source intent

Use `lettuce add-source` to create a source record under `sources/` even when the runtime is doing the real access work.

Required source-record fields, either explicit or implied by CLI defaults:

- `source_type`: email, transcript, file, stdin, telegram, github, etc.
- `stream`: where normalized events should land;
- `access_status`: `available_now`, `needs_setup`, `defer`, or `unknown`;
- `access_owner`: usually `operator-agent`;
- `sample_policy`: how much to ingest before wider backfill;
- `privacy_notes`: what to exclude or redact;
- `setup_next_action`: the smallest next step if access is not ready.

Example:

```bash
lettuce add-source email ./lettuce-acme-ken \
  --name "operator-selected customer email" \
  --address "agent-accessible mailbox" \
  --access-status available_now \
  --access-owner operator-agent \
  --sample-policy "operator-selected single-message sample before recurring ingest" \
  --privacy-notes "skip personal, legal, recruiting, and unrelated family email" \
  --setup-next-action "ingest one forwarded/customer-selected email, then inspect output" \
  --commit
```

### 4. Ingest one small sample

Use the source-specific helper when available, or the generic direct/file/stdin path when the runtime already has the content.

Direct chat signal already seen by OpenClaw:

```bash
lettuce ingest-direct ./lettuce-acme-ken \
  --title "Customer stale-context complaint" \
  --body-file /tmp/customer-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --sender "operator" \
  --consent operator-direct-request \
  --commit
```

Operator-selected email already available to the agent:

```bash
lettuce ingest-email ./lettuce-acme-ken \
  --subject "Question about stale onboarding context" \
  --body-file /tmp/customer-email.md \
  --message-id "runtime-message-id" \
  --thread-id "runtime-thread-id" \
  --from "Customer <customer@example.com>" \
  --forwarded-by operator \
  --consent operator-selected-email \
  --commit
```

Exported transcript or note:

```bash
lettuce add-source file ./lettuce-acme-ken \
  --input /tmp/customer-call.md \
  --source "file:customer-call.md" \
  --title "Customer call: stale agent context" \
  --commit
```

### 5. Run handlers and inspect output

For real dogfood inside OpenClaw, use model-backed judgment:

```bash
lettuce run ./lettuce-acme-ken --openclaw-provider --commit
```

For offline install/plumbing tests, omit `--openclaw-provider`.

The agent should summarize:

- source ingested;
- handlers that fired or skipped;
- brain updates written;
- evidence and uncertainty;
- what did not update.

If something looks wrong, the agent can edit/revert the git commit or rerun with `--review` for calibration. Do not make the human approve every routine signal.

### 6. Decide whether recurring ingest is earned

Only after the first sample proves useful should the agent propose:

- scheduled polling;
- a broader backfill;
- a forwarding rule;
- a webhook;
- OAuth/MCP setup;
- a browser-based export routine.

When recurring ingest is proposed, record it in the source record or a follow-up issue. Do not silently start broad ingestion.

## Source-specific guidance

### Direct conversation

Use the runtime's current conversation surface. Do not create a duplicate Telegram bot just for Lettuce if OpenClaw already received the signal.

### Email

Prefer operator-selected samples first. Keep consent and privacy boundaries explicit. Bulk mailbox polling is a later step after the first sample proves useful.

### Transcripts

Prefer exported transcript files first. If Fathom, Granola, Zoom, Otter, or another transcript source is already available to the runtime, record that access status and ingest a small sample before historical backfill.

### GitHub issues / Linear / work systems

For work-system signal, preserve the source URL, issue/ticket id, author when available, and whether the runtime has read-only or write access. External side effects should remain explicitly approved or governed by a standing rule.

## Public-v0 boundary

Public v0 proves the agent-operated protocol loop. It does not claim to provision source infrastructure by itself.

The honest promise is:

> Point your agent at a Lettuce repo. The agent can record source intent, ingest a selected work signal, run handlers, and commit useful company-context updates to markdown/git with provenance.

The next product step is turning one or two source records into recurring agent-owned ingest routines once the sample loop proves value.
