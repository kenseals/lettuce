# Agent-Operated Lettuce Onboarding

Lettuce is a protocol an operator's agent sets up and runs. The agent owns conversation, tool access, identity, auth, and source-specific setup. Lettuce owns the durable repo protocol: streams, handlers, brain, subscriptions, checkpoints, logs, and review/apply rules.

This document is the v0 onboarding contract for an agent runtime such as OpenClaw.

## Target UX

The operator can give a link or repo path to their agent and say:

```text
Set up Lettuce for this org.
```

The agent then walks the operator through a short setup conversation, creates or scaffolds the Lettuce repo, records source intent, and starts ingesting the signal it already has permission to see.

The operator should not need to understand the CLI first. The CLI is the agent's reliable helper for file/git/schema/checkpoint work.

The agent should not start by dumping commands or a wall of setup questions. It should first explain Lettuce in operator language, confirm the operator wants to continue, then ask one setup question at a time with enough context for the operator to understand the choice.

Onboarding is a teaching moment. First-time operators do not yet know the Lettuce mental model, so questions about repo location, sources, cadence, sample signals, and review gates should include a short “why this matters” explanation before asking for an answer. Use visible progress labels such as `Question 1/6`.

Happy-path outcome:

- the operator understands what Lettuce is and why it exists;
- the operator has one org-scoped Lettuce repo;
- at least manual/direct source ingestion is configured and explained;
- any already-available email or transcript source is recorded and sampled only within the agreed boundary;
- durable source/skill instructions are committed so the agent can keep using Lettuce after the chat ends;
- the operator receives a concise summary of what changed and how the agent will use Lettuce going forward.

Default onboarding branch: `solo_founder`. Use `multi_operator` only when the operator explicitly expects more than one personal or role-agent Lettuce and wants shared-stream coordination planned from the start.

## Core Rule

Do not build duplicate surfaces inside Lettuce.

- If the operator is talking to the agent in Telegram, iMessage, Discord, CLI, Slack, or a browser chat, that surface already belongs to the agent runtime.
- Lettuce should receive selected direct input as stream events with provenance.
- For external systems like email, Fathom, Granola, Zoom, GitHub, Linear, or Notion, the agent should first check whether it already has a connector, API, MCP, browser session, or account access before asking the operator to set anything up.

## Onboarding Phases

### 0. Explain and Confirm

Open with a short plain-English explanation:

```text
Lettuce is a work-context layer for your agent. It keeps company/org signal in a git-backed repo, separate from personal memory, then uses lenses and review gates to turn messy inputs like emails, calls, chats, and docs into durable company context your agent can use later.

I’ll ask a few setup questions, create or connect the repo, configure the first signal sources, and leave you with a summary of what I set up and how I’ll use it going forward.

Want to continue?
```

If the operator says no, stop. If they say yes, continue.

Do not ask every possible setup question up front. Ask the minimum needed to establish the repo and first sources, then inspect what the agent can already access. Prefer a conversational sequence over a questionnaire dump.

### 1. Anchor the Organization

Ask for the organization or project this Lettuce is for.

Required output:

- org name/slug
- operator handle/name
- whether this is a personal, company, client, or project Lettuce

Operator-facing phrasing:

```text
What company, client, or project is this Lettuce for? You can add more Lettuces later for other orgs so the contexts do not bleed together.
```

Why this matters: one operator can have multiple Lettuces. Work context for different orgs should not bleed together.

### 2. Choose or Create the Repo

Before repo creation, choose the onboarding branch:

- `solo_founder`: default and preferred. Create one personal Lettuce repo, configure manual/direct ingestion, record one source plan, run the first handler pass, optionally offer GitHub remote setup, and mention shared streams only as future-ready context.
- `multi_operator`: optional. Create one personal or role-agent Lettuce repo first, then record intent for GitHub-org discovery of personal, role-agent, and hub candidates. If no hub exists, offer `lettuce-<org>-hub`. Subscribe only to explicit exported streams, keep future mirrors under `streams/shared/*`, and run local handlers before any local brain promotion from shared signal.

Do not make the multi-operator branch block first setup. If discovery or hub decisions are not ready, record the plan in `onboarding/setup/handoff.json` and continue with the local repo.

Ask whether the operator wants to:

- use an existing repo
- create a new private repo manually and provide the URL/path
- let the agent create the repo if it has permission
- start locally first and push later

Explain this choice before asking. Operator-facing framing:

```text
Question 2/6: Where should this Lettuce live?

The repo is Lettuce's local markdown+git work brain. Starting local is easiest for a first test. An existing repo/path or later private GitHub remote is useful when you want backup, sync, or another agent/machine to access the same context.
```

Agent action for normal first setup:

```bash
lettuce onboard <repo-path> \
  --org <org> \
  --operator <operator> \
  --title "<first direct signal title>" \
  --body-file <tmp-signal.md> \
  --source "<agent.surface>" \
  --surface "<surface>" \
  --consent "<basis>" \
  --source-plan '{"source_type":"email","name":"customer-mailbox","address":"customers@example.com","access_status":"available_now","sample_policy":"first-3-operator-approved"}' \
  --source-plan '{"source_type":"granola","name":"sales-calls","workspace":"team-granola","access_status":"needs_setup","setup_next_action":"connect existing export or MCP before polling"}' \
  --cadence-hint "manual-for-now" \
  --cadence-trigger "when-asked" \
  --handoff-summary "Direct chat is available now; email is the next ready recurring source; transcripts still need setup." \
  --openclaw-provider \
  --review \
  --commit
```

For one-sentence smoke tests, `--body "<first direct signal body>"` is fine. For real operator messages, pasted transcripts, or multi-paragraph signal, prefer `--body-file` so the agent preserves the exact text and avoids shell quoting mistakes. If neither body option is provided, `lettuce onboard` reads stdin. Use `--openclaw-provider` for real OpenClaw dogfood so handlers make judgment calls instead of using the deterministic fallback adapter. Use `--review` for onboarding so first-pass handler output becomes explicit pending review proposals before any durable brain write.

`lettuce onboard` now also writes `onboarding/setup/handoff.json`. That handoff is the repo-owned machine-readable record of:

- the chosen onboarding branch (`solo_founder` or `multi_operator`);
- source plan entries and access/setup state;
- cadence/trigger hints for future refresh;
- the first sample type/source/event path;
- the first sample outcome; and
- a concise summary for the next agent handoff.

When the branch is `multi_operator`, the handoff may also record lightweight discovery notes and intent for personal/role-agent/hub candidates. It must not falsely imply that GitHub org scanning, remote mirroring, or `pull-subscriptions` are already shipped in Lettuce itself.

Use `--source-record <id-or-path>` when the source records already exist under `sources/` and should just be referenced in the handoff.

For manual control, the agent can run the lower-level steps directly:

```bash
lettuce init <repo-path> --org <org> --operator <operator>
lettuce discover <repo-path>
lettuce status <repo-path>
```

### 3. Source Discovery

Ask what company signal matters for this Lettuce, then inspect what the agent already has access to. Do not force the operator to enumerate every source cold.

Operator-facing phrasing:

```text
What signal sources should this Lettuce pay attention to first? Common ones are email, meeting transcripts, customer/support threads, Slack/Discord, GitHub/Linear, docs, and direct messages you forward to me. We can start with manual forwarding if you do not want to connect anything yet.
```

Better first-run flow:

```text
Question 4/6: Which sources should I look for first?

Sources are where company signal comes from. I can start by checking what I already have access to, then we can mark each source as available now, needs setup, or later. Common sources are direct notes, email, transcripts, GitHub/Linear, docs, Slack/Discord, and manual file drops.
```

Use this order:

1. Direct operator input through the current agent conversation.
2. Email or inboxes the agent can access.
3. Meeting/call transcript systems available through tools, APIs, MCP, browser, or exports.
4. Work systems such as GitHub, Linear, Notion, Slack, Docs, CRM, support tools.
5. Manual file drops or pasted links.

The first setup should almost always configure **manual/direct ingestion** even if no other source is available. This gives the operator an immediate way to say “run Lettuce on this” and get a review packet without OAuth, connectors, or polling.

For many users, also try to configure one recurring source if available without heavy setup:

- email: operator-selected threads, labels, forwarding, or existing agent mailbox access;
- transcripts: Fathom, Granola, Zoom/Otter/Meet exports, or transcript email summaries;
- work systems: GitHub/Linear/Notion/Slack only when the agent already has scoped access.

Do not bulk-ingest during onboarding. A first source is “set up” when source intent is recorded, privacy/sample policy is clear, and a tiny sample path exists.

For every source discussed, the handoff must answer:

- Did we actually configure it, or just record intent?
- Can the agent access it now?
- What sample is allowed before bulk ingestion?
- What privacy boundary applies?
- What trigger/cadence applies, such as manual, daily email check, after meetings, or operator-selected only?
- What is the next setup action if access is not ready?

For each candidate source, classify:

- `available_now`: agent already has access and can ingest with standing consent or explicit approval.
- `needs_setup`: operator must connect OAuth, forwarding, export, webhook, MCP, or browser session.
- `defer`: useful later, but not worth onboarding friction today.
- `manual-only`: the runtime can ingest only when the operator forwards, pastes, exports, or explicitly points to the source. Treat this as a recipe posture and persist the closest truthful CLI `access_status`.

### 4. Record Source Intent

For direct input, no source adapter is needed. The agent writes events directly:

```bash
lettuce ingest-direct <repo-path> \
  --title "<short signal title>" \
  --body "<signal body>" \
  --source "openclaw.telegram" \
  --surface "telegram" \
  --message-id "<message-id>" \
  --chat-id "<chat-or-topic-id>" \
  --sender "<operator>" \
  --consent "operator-direct-request" \
  --commit
```

For operator-forwarded or selected email, keep the event email-shaped:

```bash
lettuce ingest-email <repo-path> \
  --subject "<email subject>" \
  --body-file <tmp-email-summary.md> \
  --message-id "<message-id>" \
  --thread-id "<thread-id>" \
  --from "<sender>" \
  --forwarded-by "<operator>" \
  --consent "operator-forwarded-email" \
  --commit
```

For source systems that need durable records, use source config files:

```bash
lettuce add-source email <repo-path> --name <name> --address <address-or-account> --access-status available_now --sample-policy first-5-operator-approved --commit
lettuce add-source granola <repo-path> --name <name> --workspace <workspace> --access-status needs_setup --setup-next-action "connect existing export or MCP before polling" --commit
```

The source record is a setup/status contract for the operator's agent. It should say whether the agent can sample now, what privacy boundary applies, and what the next setup step is. Supported transcript records include `fathom`, `granola`, `zoom`, and generic `transcript`.

For manual/direct ingestion, make the behavior durable too. The operator's agent should write repo-local instructions in `LETTUCE_AGENT.md` at the repo root saying:

- what phrase triggers manual ingestion, such as "run Lettuce on this";
- which repo/org it should use by default;
- what provenance and consent fields to preserve;
- whether review is required before `brain/*` writes;
- what kinds of personal/private signal should be skipped.
- where to inspect `sources/*.md` for current source status, privacy notes, and setup next actions;
- what cadence is configured, or that the repo is manual/agent-triggered for now.

Runtime-specific skills, prompts, and wrappers should point to `LETTUCE_AGENT.md` first, then inspect `sources/*.md` for the current source contract.

### 5. First Ingestion

Pick the lowest-friction real signal and process it end-to-end.

For direct input after initial onboarding:

```bash
lettuce ingest-direct <repo-path> --title "<title>" --body "<body>" --source "<agent.surface>" --surface "<surface>" --consent "<basis>" --commit
lettuce run <repo-path> --review --commit
lettuce reviews <repo-path>
lettuce status <repo-path>
lettuce logs <repo-path> --limit 5
```

For email/transcripts/work systems:

1. Pull a small sample, usually 1-5 items.
2. Write each selected item as a stream event with provenance.
3. Run handlers.
4. Show the operator the brain entries and skipped/noisy results.

Do not bulk-ingest during first onboarding unless the operator explicitly asks for it.

After the first run, use `lettuce status` to confirm the maintenance posture matches the real contract: `pending_review` when reviews are waiting, `blocked_on_setup` when access is not ready, `idle_manual_only` when only operator-triggered capture exists, or `fresh` when a runnable maintenance path is configured and inspectable.

### 6. OpenClaw Skill Wrapper

For OpenClaw, the skill should wrap the CLI rather than expose it as operator work:

1. Explain Lettuce briefly and confirm the operator wants to continue.
2. Ask only for missing org, operator, repo path/start-local preference, first manual signal if needed, and consent basis.
3. Ask which signal sources should be configured first; inspect existing OpenClaw access before asking the operator to connect anything.
4. Write the first signal to a temporary UTF-8 markdown file when it is longer than a sentence.
5. Run `lettuce onboard` with `--body-file`, provenance fields, `--openclaw-provider`, `--review`, and `--commit`.
6. Configure manual/direct ingestion as the baseline source and record source intent for any available email/transcript/work source.
7. Parse stdout JSON and translate it into a short operator summary.
8. Keep stderr progress available for debugging, but do not paste raw logs unless needed.

The summary should include:

- repo initialized or reused
- event path and source provenance
- handlers/events processed
- pending review paths written
- skipped/errors/noise
- current log/checkpoint count
- configured source records and whether they are `available_now`, `needs_setup`, or deferred
- whether any recurring schedule exists; if none, say that new signal sampling is manual/agent-triggered for now
- whether `onboarding/setup/handoff.json` was recorded and what cadence/source-plan state it contains

Then ask exactly one review question:

```text
Approve, edit, or decline these proposed updates?
```

If the operator says approve, run `lettuce review-approve <repo> <review-id> --operator <operator> --commit` for each approved item and recommend the next source to sample. If they say edit, make the smallest markdown edit in the pending review file first, then approve it. If they say decline, run `lettuce review-decline <repo> <review-id> --reason "<short reason>" --operator <operator> --commit`. Avoid direct publishing during onboarding unless the operator explicitly asks to bypass review.

End onboarding with a concise durable summary:

```text
Done. I set up Lettuce for <org> at <repo>. Manual/direct ingestion is ready, so you can say “run Lettuce on this” and I’ll capture the signal with provenance, run lenses, and show review proposals before durable brain updates. I also recorded <sources> with <sample/privacy policy>. Going forward I’ll use this Lettuce for <org>-scoped work context, not personal memory, and I’ll ask before bulk ingesting or writing sensitive updates.
```

Also surface the repo-local instruction path, for example: `Repo-local agent instructions: <repo>/LETTUCE_AGENT.md`.

If recurring checks are configured, say exactly what cadence/trigger owns them. If they are not configured yet, say what the operator needs to connect or forward next.

Future multi-operator setup: once shared streams are implemented, onboarding should also scan the relevant GitHub org/account for existing repos containing `lettuce.yml`, summarize candidate streams, and ask before subscribing to any shared org stream.

## Source Recipes

Detailed source-discovery recipes live in `docs/source-discovery-recipes.md`. For concrete agent-readable patterns and handoff language, use `docs/source-recipes/README.md` plus the matching recipe under `docs/source-recipes/` before building new adapters or asking the operator for setup.

### Direct Input

The agent already received the signal. Preserve provenance when useful:

- surface: `openclaw.telegram`, `openclaw.imessage`, `discord`, `cli`, `browser-chat`
- chat/topic/message id when available
- sender/operator identity
- timestamp
- explicit consent or standing rule basis

Default stream: `streams/inbox/direct`.

### Email

First ask whether the agent already has mailbox access.

If yes:

- search/filter a small sample
- ask before ingesting sensitive or private mail
- write selected emails to `streams/inbox/email`
- preserve sender, recipients, subject, timestamp, message/thread id, and source mailbox

If no:

- guide the operator to connect Gmail/IMAP/provider access, or create forwarding/export flow
- record source intent in `sources/<source>.md`
- do not pretend access exists

### Call Transcripts

First check available tools/connectors/MCP/browser access for Fathom, Granola, Zoom, Otter, Meet, or exported transcript files.

If available:

- start with a small recent sample
- preserve call title, participants if safe, timestamp, transcript source, and URL/id
- write selected transcripts to `streams/inbox/transcripts`

If unavailable:

- guide setup for whichever tool the operator already uses
- prefer exports/manual file drops before building custom OAuth

### Work Systems

For GitHub, Linear, Notion, Slack, docs, CRM, or support systems:

- use the agent's existing connectors where possible
- ingest only signal relevant to the scoped org/project
- preserve source URL/id and permission context
- avoid copying private unrelated data into the Lettuce repo

## V0 Success Criteria

A new operator can ask their agent to set up Lettuce and end up with:

- a short Lettuce explanation and explicit confirmation to continue
- a repo initialized with `lettuce.yml`
- default handlers discovered
- at least one direct signal ingested through the agent
- one handler run committed to git
- one useful pending review proposal or approved brain entry
- visible logs/checkpoints
- manual/direct ingestion durably configured as the fallback source
- any available first email/transcript/work source recorded with access status, sample policy, and privacy notes
- a clear next source recommendation
- a final operator summary of what was set up and how the agent will use Lettuce going forward

Time target: under 15 minutes for direct-input-only onboarding.

## Do Not

- Do not build a separate Telegram bot just to prove direct input.
- Do not ask the operator to configure sources the agent can already access.
- Do not bulk-ingest before a small reviewed sample proves the source is useful.
- Do not hide auth/setup failures behind generic source records.
- Do not mix personal-life context into an org-scoped Lettuce.
