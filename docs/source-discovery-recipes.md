# Source Discovery Recipes

These recipes tell an operator's agent how to decide whether and how to connect signal sources to Lettuce.

Lettuce does not own service auth, inboxes, chat surfaces, OAuth, browser sessions, or MCP connectors. The agent owns access and setup. Lettuce owns source records and stream events.

For concrete agent-readable recipe files, use `docs/source-recipes/README.md` and the recipes under `docs/source-recipes/`.

## General Source Discovery Loop

For every source class:

1. Ask what kind of signal the operator expects from the source.
2. Check whether the agent already has access through connectors, MCP, local files, browser session, API token, or existing account permissions.
3. Classify the source:
   - `available_now`: agent can inspect and ingest a small sample now.
   - `needs_setup`: operator must connect, export, forward, grant OAuth, or provide a file/API token.
   - `defer`: useful later but not needed for the first working Lettuce.
   - `manual-only`: the runtime can ingest only when the operator forwards, pastes, exports, or explicitly points to the source. This is an agent recipe posture, not a CLI `access_status` enum; persist the closest truthful `access_status` and state manual-only behavior in the source record.
4. If available, ingest a small sample first, usually 1-5 items.
5. Run handlers and review output before bulk backfill.
6. Record durable source intent under `sources/` when the source will recur.
7. If the source should be checked regularly, record the owner and cadence/trigger in the source record. The agent runtime owns the actual recurring check; Lettuce records the contract so future runs are inspectable.

Do not bulk-ingest before a small reviewed sample proves the source is useful.

Do not try to maintain a complete source-specific feature catalog during onboarding. The agent should use source recipes to ask the right questions, inspect current runtime access, choose a connection plan, and record the truth. Real source capability discovery belongs to the runtime/tooling at setup time.

Before asking detailed source questions, show a source card that explains the source in operator language: useful signal, access methods, what connected means, first safe sample, recommended trigger, and future automation requirements.

For each source, decide the intended connection mode:

- `manual-only`: operator forwards, pastes, exports, or points at selected items.
- `after-event`: runtime reacts when a transcript, notification, exported file, or forwarded item appears.
- `polling/cron`: runtime checks a scoped query/project/mailbox/channel on a schedule.
- `webhook`: runtime receives authenticated events from the source and dedupes them before writing stream events.

Default bias: manual or polling first, webhook only when event delivery, auth, dedupe, and scope control are clear.

Also record routing status separately from access status. Example: an agent may have a mailbox and daily email cron (`access_status: available_now`) while Lettuce-specific email routing still needs validation (`routing_status: needs_validation`).

Manual/direct ingestion should be available for every first setup even when no recurring source is ready. It is the default fallback path: the operator forwards or pastes a signal and says “run Lettuce on this.”

Mapped agent-owned chat surfaces are more proactive than manual fallback. If the runtime is already receiving a conversation from Telegram, Slack, Discord, iMessage, browser chat, or CLI, and a source record maps that `surface` plus optional `chat_id`, `thread_id`, or `topic`, the agent should route material org signal under the recorded `capture_policy` and `standing_rule` without waiting for the operator to name Lettuce. Lettuce still does not own the chat connection; it records the durable route contract and captured events.

For mapped chat surfaces, source records may include:

- `surface`: runtime surface such as `telegram` or `slack`.
- `chat_id`: channel, chat, or room id.
- `thread_id`: thread, topic, or forum id.
- `topic`: human-readable thread/topic label.
- `capture_policy`: which material signal belongs in Lettuce.
- `standing_rule`: consent or standing instruction that authorizes recurring capture.
- `route_policy`: how to answer/audit routing questions such as “are you saving this?”
- `local_auto_apply`: whether low-risk local updates covered by the standing rule can skip a heavy review gate.

Use `lettuce route-audit` when an operator asks whether a surface is being saved. The audit should inspect matching source records, recent matching stream events, and review proposals tied to those events.

For onboarding-path decisions:

- `solo_founder` stays minimal. Record the personal repo, direct/manual source, one next source plan, and the first reviewed sample. Shared streams are future-ready context, not required setup work.
- `multi_operator` is optional. Record likely personal, role-agent, and hub candidates plus shared-stream intent, but do not block local setup waiting on org-wide discovery. Any future shared import must stay under `streams/shared/*`, use explicit exported streams only, and run through local handlers before local brain promotion.

## Agent-Readable Recipe Pattern

Every concrete recipe should specify:

1. required runtime access;
2. operator questions;
3. source record command;
4. privacy/sample defaults;
5. first tiny sample path;
6. verification checks;
7. operator handoff.

Recipe library:

- `docs/source-recipes/direct-manual.md`
- `docs/source-recipes/email-recurring.md`
- `docs/source-recipes/transcripts-after-meeting.md`
- `docs/source-recipes/work-systems-github-linear.md`

## Recipe Routing Table

Use this table during onboarding. The agent should name the recipe it is using so the operator understands what is being configured.

| Source class | Recipe | Default stream | First setup posture |
| --- | --- | --- | --- |
| Direct notes / pasted signal | `direct-manual.md` | `streams/inbox/direct` | Always configure; manual-only trigger. |
| Email / mailbox / forwarded thread | `email-recurring.md` | `streams/inbox/email` | Sample-first; daily only after useful review output. |
| Meeting transcripts / call summaries | `transcripts-after-meeting.md` | `streams/inbox/transcripts` | After-meeting or operator-selected; 1-3 sample calls first. |
| GitHub / Linear / docs / Slack / Notion | `work-systems-github-linear.md` | `streams/inbox/work` | Scoped repo/project/channel only; record access honestly. |

Recipe-driven onboarding rule: after a source is selected, do not move on until the operator knows whether the source was actually configured, what can be sampled now, what cadence/trigger applies, and what setup action remains.

## Email

For the full recipe, see `docs/source-recipes/email-recurring.md`.

### Discovery Questions

- Which mailbox or email account contains the relevant org signal?
- Is the signal mostly inbound customer mail, internal decisions, vendor updates, support threads, or newsletter/reference material?
- Should the agent ingest from search queries, labels/folders, forwarded messages, or manually selected threads?
- Are there privacy boundaries: personal mail, family, legal, medical, recruiting, finance, or unrelated orgs?

### Access Check

The agent should check for:

- Gmail connector access.
- IMAP/SMTP or provider API credentials already available.
- Existing forwarding address or mailbox rules.
- Exported `.eml`, `.mbox`, markdown, or pasted email content.
- Browser access to the mailbox when appropriate and operator-present.

### If Available Now

Start with a targeted query or manually selected thread. For each ingested email, preserve:

- source mailbox
- message id/thread id
- subject
- sender/recipients when safe
- timestamp
- source URL if available
- query/label/folder used
- redaction notes if any

Default stream: `streams/inbox/email`.

Use source intent:

```bash
lettuce add-source email <repo-path> \
  --name <mailbox-or-filter-name> \
  --address <mailbox-or-account-label> \
  --access-status available_now \
  --sample-policy first-5-operator-approved \
  --privacy-notes "skip personal/legal/medical/unrelated mail" \
  --commit
```

Then write selected messages as stream events using `ingest-email` for operator-forwarded or operator-selected emails:

```bash
lettuce ingest-email <repo-path> \
  --subject "<email subject>" \
  --body-file <email-summary-or-body.md> \
  --message-id <message-id> \
  --thread-id <thread-id> \
  --from "<sender>" \
  --forwarded-by <operator> \
  --consent operator-forwarded-email \
  --commit
```

Use `add-source file` for exported `.eml`, `.mbox`, or markdown files when direct Gmail metadata is unavailable.

### If Setup Is Needed

Prefer the lowest-friction route:

1. Ask operator to select/forward a few example messages manually.
2. Use Gmail connector/OAuth if available in the agent runtime.
3. Create a forwarding rule or dedicated address only if repeated ingestion needs it.
4. Defer provider-specific webhook infrastructure until repeated usage proves it.

## Call Transcripts

Use the email recipe as the pattern baseline, but adapt runtime access and privacy boundaries to transcript tools and exports.

### Discovery Questions

- Which meeting/transcript tool does the operator already use: Fathom, Granola, Zoom, Otter, Google Meet, Fireflies, Gong, etc.?
- What kind of calls matter: sales, customer success, recruiting, internal strategy, product discovery, investor, support?
- How far back should the first sample go?
- Which participants or orgs are in scope?
- Are there consent/privacy rules for transcript ingestion?

### Access Check

The agent should check for:

- Existing MCP/API connector for the transcript tool.
- Local exported transcripts.
- Email notifications containing transcript links or summaries.
- Browser access to the transcript app when operator-present.
- Calendar events with meeting links that can anchor discovery.

### If Available Now

Start with 1-3 recent transcripts in the scoped org/project. Preserve:

- transcript tool/source
- call title
- call timestamp
- participants when safe
- source URL/id
- export path if file-based
- consent/availability basis
- redaction notes if any

Default stream: `streams/inbox/transcripts`.

Use source intent:

```bash
lettuce add-source granola <repo-path> \
  --name <source-name> \
  --workspace <workspace-or-account> \
  --access-status needs_setup \
  --sample-policy first-3-operator-approved \
  --setup-next-action "connect existing export, MCP, or OAuth before polling" \
  --commit
```

The CLI supports `fathom`, `granola`, `zoom`, and generic `transcript` records. These are setup/status records, not provider-specific pollers.

### If Setup Is Needed

Prefer:

1. Operator exports or shares one transcript file.
2. Agent uses an existing connector/MCP if available.
3. Operator grants OAuth/API access for the tool they already use.
4. Build polling/backfill only after a sample run proves value.

## Work Systems

Examples: GitHub, Linear, Notion, Slack, Google Docs, support tools, CRM.

For the full recipe, see `docs/source-recipes/work-systems-github-linear.md`.

### Discovery Questions

- Which system already contains decisions, customer signal, or work state?
- Is the agent already connected to it?
- Which project/team/repo/channel/database is in scope?
- What should be ingested: decisions, issues, comments, docs, messages, status changes, customer requests?

### Access Check

Use existing agent connectors first. Do not create new Lettuce-specific auth when the agent can already inspect the system.

### If Available Now

Start with a bounded sample:

- 3-10 recent issues/messages/docs/records
- one project/team/channel/repo at a time
- source URLs and ids preserved
- no unrelated private context copied into the Lettuce repo

Default streams depend on source shape:

- GitHub/Linear/docs/Slack/Notion setup records: `streams/inbox/work`
- decisions/docs bridged through chat when no work-system stream handlers exist yet: `streams/inbox/direct`
- customer/support email-shaped signal: `streams/inbox/email` or a future support stream

## Source Record Shape

A durable source record should make future agent behavior obvious:

```markdown
---
id: email-support-forward
type: email
name: support-forward
status: configured
stream: streams/inbox/email
created_at: 2026-05-02T00:00:00Z
access_status: available_now
access_owner: operator-agent
sample_policy: first-5-operator-approved
privacy_notes: skip personal/legal/medical unrelated mail
setup_next_action: sample five messages from label:customers before bulk ingest
check_policy: manual until first sample approved; then agent checks label daily
---

# support-forward

What this source contains, how the agent has access, what should be ingested, what should be skipped, and what setup remains.
```

Use the source record to make the agent's behavior inspectable. Do not let setup knowledge live only in chat memory.

For future shared-stream onboarding, source discovery should also scan for existing Lettuce repos containing `lettuce.yml` in the operator's org/account once shared streams are implemented. Treat discovered streams like sources: summarize what exists, classify access, and ask before subscribing.
