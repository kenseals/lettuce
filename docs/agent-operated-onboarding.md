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

The operator should also not be surprised by setup. First use is a guided onboarding conversation, not a silent automation. The agent should explain what Lettuce is, ask a few setup questions, confirm assumptions, then run the first review-mode loop.

## First Response Contract

When an operator provides the repo or `llms.txt` link and asks to set up Lettuce, the agent should not immediately initialize a repo or ingest the setup request.

First say, briefly:

> Lettuce gives your agent a local markdown+git work brain for one company/project. It keeps work context separate from personal memory, records which sources should feed that context, and lets the agent keep useful company context fresh from signals it can access. The point is not to make you review every signal; it is to give the agent durable work context it can use later.

Then ask the minimum setup questions:

1. Which work context is this for?
2. Should we start locally first, or use an existing repo/path?
3. What signal sources should eventually feed it?
4. What one small meaningful sample signal should we ingest first?
5. What cadence or trigger should keep it fresh? For example: manual for now, daily, after meetings, when asked, or a project-specific agent lane.
6. Should I run that sample now and show you what context was added?

If the conversation already implies an answer, summarize it as an assumption and ask for confirmation. Example: "I think this is for The Ultra Minute and we should start locally first. Is that right?"

Do not use the setup request itself as the first signal unless the operator explicitly says to. A setup request usually creates vague setup-context reviews that feel random to the operator. Prefer a real signal from the scoped work context.

## Core Rule

Do not build duplicate surfaces inside Lettuce.

- If the operator is talking to the agent in Telegram, iMessage, Discord, CLI, Slack, or a browser chat, that surface already belongs to the agent runtime.
- Lettuce should receive selected direct input as stream events with provenance.
- For external systems like email, Fathom, Granola, Zoom, GitHub, Linear, or Notion, the agent should first check whether it already has a connector, API, MCP, browser session, or account access before asking the operator to set anything up.

## Onboarding Phases

### 1. Anchor the Organization

Ask for the organization or project this Lettuce is for.

Required output:

- org name/slug
- operator handle/name
- whether this is a personal, company, client, or project Lettuce

Why this matters: one operator can have multiple Lettuces. Work context for different orgs should not bleed together.

Also ask what benefit the operator expects from this Lettuce. Keep it lightweight: "What should this help your agent remember or notice for this work context?" This helps avoid creating a repo that technically works but has no clear user value.

### 2. Choose or Create the Repo

Ask whether the operator wants to:

- use an existing repo
- create a new private repo manually and provide the URL/path
- let the agent create the repo if it has permission
- start locally first and push later

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
  --openclaw-provider \
  --commit
```

For one-sentence smoke tests, `--body "<first direct signal body>"` is fine. For real operator messages, pasted transcripts, or multi-paragraph signal, prefer `--body-file` so the agent preserves the exact text and avoids shell quoting mistakes. If neither body option is provided, `lettuce onboard` reads stdin. Use `--openclaw-provider` for real OpenClaw dogfood so handlers make judgment calls instead of using the deterministic fallback adapter. Omit `--review` by default; routine local brain updates should land with provenance and git history. Use `--review` only for optional calibration, sensitive sources, high-impact changes, or when the operator asks to inspect before applying.

For manual control, the agent can run the lower-level steps directly:

```bash
lettuce init <repo-path> --org <org> --operator <operator>
lettuce discover <repo-path>
lettuce status <repo-path>
```

### 3. Source Discovery

Ask what company signal matters for this Lettuce, then inspect what the agent already has access to.

Use this order:

1. Direct operator input through the current agent conversation.
2. Email or inboxes the agent can access.
3. Meeting/call transcript systems available through tools, APIs, MCP, browser, or exports.
4. Work systems such as GitHub, Linear, Notion, Slack, Docs, CRM, support tools.
5. Manual file drops or pasted links.

For each candidate source, classify:

- `available_now`: agent already has access and can ingest with standing consent or explicit approval.
- `needs_operator_setup`: operator must connect OAuth, forwarding, export, webhook, MCP, or browser session.
- `not_now`: useful later, but not worth onboarding friction today.

Explain the source plan before running. A good first setup says: "For now I will configure direct chat notes as available, mark email/transcripts as not set up unless you want to connect them, and use one sample you approve. There is no automatic schedule yet; new signals are sampled when you ask or when a configured agent lane runs."

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

### 5. First Ingestion

Pick the lowest-friction real signal and process it end-to-end.

For direct input after initial onboarding:

```bash
lettuce ingest-direct <repo-path> --title "<title>" --body "<body>" --source "<agent.surface>" --surface "<surface>" --consent "<basis>" --commit
lettuce run <repo-path> --commit
lettuce status <repo-path>
lettuce logs <repo-path> --limit 5
```

For email/transcripts/work systems:

1. Pull a small sample, usually 1-5 items.
2. Write each selected item as a stream event with provenance.
3. Run handlers.
4. Show the operator the brain entries and skipped/noisy results.

Do not bulk-ingest during first onboarding unless the operator explicitly asks for it.

### 6. OpenClaw Skill Wrapper

For OpenClaw, the skill should wrap the CLI rather than expose it as operator work:

1. Explain Lettuce in one short paragraph and ask/confirm org, operator, repo path, source candidates, first meaningful sample, and consent basis.
2. Write the first signal to a temporary UTF-8 markdown file when it is longer than a sentence.
3. Run `lettuce onboard` with `--body-file`, provenance fields, `--openclaw-provider`, and `--commit`.
4. Parse stdout JSON and translate it into a short operator summary.
5. Keep stderr progress available for debugging, but do not paste raw logs unless needed.

The summary should include:

- repo initialized or reused
- event path and source provenance
- handlers/events processed
- brain updates written, each with a human explanation of what it added and why it matters
- skipped/errors/noise
- current log/checkpoint count
- configured source records and whether they are `available_now`, `needs_setup`, or deferred
- whether any recurring schedule exists; if none, say that new signal sampling is manual/agent-triggered for now

If something looks wrong, offer to edit or revert the git commit. Do not turn normal operation into a standing approval queue.

Then give a final handoff:

- where the Lettuce repo lives;
- what it is scoped to;
- what sources are configured and what setup remains;
- how new signals get into it today;
- what the operator should ask the agent next if they want more value.

## Source Recipes

Detailed source-discovery recipes live in `docs/source-discovery-recipes.md`. Use those before building new adapters or asking the operator for setup.

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

- a repo initialized with `lettuce.yml`
- default handlers discovered
- at least one direct signal ingested through the agent
- one handler run committed to git
- one useful brain entry written
- visible logs/checkpoints
- a clear next source recommendation

Time target: under 15 minutes for direct-input-only onboarding.

## Do Not

- Do not build a separate Telegram bot just to prove direct input.
- Do not ask the operator to configure sources the agent can already access.
- Do not bulk-ingest before a small reviewed sample proves the source is useful.
- Do not hide auth/setup failures behind generic source records.
- Do not mix personal-life context into an org-scoped Lettuce.
