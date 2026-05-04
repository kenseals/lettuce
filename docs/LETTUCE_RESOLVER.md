# Lettuce Ongoing-Use Resolver

Use this after setup when an operator already has an org-scoped Lettuce and wants the agent to keep using it safely.

This resolver is for ongoing company/project context, not first-time onboarding. For setup, start with `AGENTS.md`, `INSTALL_FOR_AGENTS.md`, and `docs/agent-operated-onboarding.md`.

## What This Resolver Decides

When the operator asks for work help, decide whether to:

- look up org-scoped Lettuce context before answering;
- ingest a new signal into Lettuce and run handlers;
- update source or subscription records;
- walk the review approve/edit/decline loop;
- do recurring maintenance on sources or shared streams;
- skip Lettuce because the request is personal, ephemeral, or outside the product boundary.

## Core Boundary

Keep these rules true on every run:

- Use one Lettuce per org/project/work context. Do not mix unrelated companies, clients, or personal life.
- The runtime owns chat surfaces, inboxes, browser sessions, OAuth, MCP connectors, API keys, and schedules.
- Lettuce owns durable repo state: `lettuce.yml`, `streams/*`, `handlers/*`, `brain/*`, `sources/*`, `subscriptions/*`, `reviews/*`, `.lettuce/*`, and git history.
- Do not build duplicate chat, email, browser, or OAuth surfaces inside Lettuce.
- Do not treat Lettuce as personal memory. If the operator's request is personal or cross-org, keep it out of an org-scoped Lettuce unless they explicitly want a separate Lettuce for that context.

## Resolver Loop

When a new operator request arrives:

1. Identify the org/project scope and the matching Lettuce repo.
2. Decide whether the request needs existing company context, new ingestion, both, or neither.
3. If context is needed, read the smallest relevant Lettuce state first.
4. If new signal should become durable context, ingest it with provenance, then run handlers.
5. If review mode is in effect, ask for approve, edit, or decline before durable `brain/*` writes land.
6. End with a short handoff: what you looked up, what you ingested, what changed, and what the next trigger/cadence is.

## Trigger: Look Up Org Context Before Answering

Check Lettuce before answering when the operator asks about:

- company decisions, policies, customers, roadmap, incidents, pricing, or ongoing projects;
- what happened recently in a scoped org/project;
- whether a customer, partner, or teammate signal was already captured;
- what the current durable context says before drafting a reply, plan, or recommendation.

Read the smallest useful surface first:

- `brain/*` for durable context;
- recent `streams/*` events if the question is about new signal;
- `sources/*` if the question is about what feeds the repo;
- `subscriptions/*` if the question is about teammate/shared context;
- `.lettuce/logs/` or `lettuce logs` only when debugging run behavior.

Do not scan the whole repo by default. Read only what is needed for the answer.

## Trigger: Manual/Direct Ingestion

Use Lettuce when the operator says things like:

- "run Lettuce on this"
- "capture this for Acme"
- "put this into the work brain"
- "use this call/email/note for future context"

Expected command shape:

```bash
lettuce ingest-direct <repo-path> \
  --title "<short title>" \
  --body-file <tmp-signal.md> \
  --source <agent.surface> \
  --surface <surface> \
  --consent operator-direct-request \
  --commit
lettuce run <repo-path> --review --commit
lettuce reviews <repo-path>
```

Preserve provenance when available: source, surface, sender, message id, thread/topic/chat id, observed timestamp, and consent basis.

Use `ingest-email` instead of flattening an email into direct input when the operator forwards or selects an email thread.

## Trigger: Source Setup Or Update

Reach for source records when the operator asks to connect, change, or inspect ongoing sources such as email, transcripts, GitHub, Linear, Notion, Slack, docs, CRM, support tools, or local export folders.

Follow this order:

1. Check whether the runtime already has access.
2. Classify the source as `available_now`, `needs_setup`, or `defer`.
3. Record or update the source contract under `sources/*`.
4. Sample small before any backfill.

Expected command shape:

```bash
lettuce add-source <type> <repo-path> \
  --name <name> \
  --access-status <available_now|needs_setup|defer> \
  --sample-policy "<small-sample rule>" \
  --setup-next-action "<smallest next setup step>" \
  --commit
```

The runtime owns the real connector, browser, OAuth, forwarding, export, or polling work. Lettuce records the durable contract so future runs are inspectable.

## Trigger: Review Approve, Edit, Or Decline

Use the review loop when onboarding, calibrating a new handler/source, handling sensitive updates, or whenever the operator wants approval before durable context changes.

Flow:

1. Run with `--review`.
2. Show the pending review proposals in operator language.
3. Ask one short question: approve, edit, or decline?
4. If approve, publish with `review-approve`.
5. If edit, make the smallest markdown edit to the pending review file, then approve it.
6. If decline, archive it with `review-decline` and record a short reason.

Expected commands:

```bash
lettuce reviews <repo-path>
lettuce review-approve <repo-path> <review-id> --operator <operator> --commit
lettuce review-decline <repo-path> <review-id> --operator <operator> --reason "not useful" --commit
```

There is no separate `review-edit` command in v0. Edit the pending review markdown directly, then approve.

## Trigger: Recurring Or Maintenance Runs

Use Lettuce maintenance when the operator asks for a recurring cadence or when an already-configured source should be checked again.

Common cases:

- "check the support mailbox every morning"
- "pull today's meeting transcripts into the Acme Lettuce"
- "refresh the context before our Monday planning"
- "what sources still need setup?"

Rules:

- The runtime owns the actual scheduler or cron.
- Lettuce should record the cadence/trigger contract in `sources/*`.
- Keep maintenance sample-first for newly connected sources.
- Use `lettuce status`, `lettuce logs`, and source records to explain what happened.

If no recurring trigger is configured, say so plainly: manual/agent-triggered for now.

## Trigger: Subscriptions And Shared Streams

Use subscriptions when the operator wants scoped context from another Lettuce, such as a teammate or shared org stream.

Rules:

- Ask before subscribing to a remote/shared stream.
- Preserve the local boundary with an explicit mirror path such as `streams/shared/*`.
- Treat subscription setup as durable intent, not magic federation.

Expected command shape:

```bash
lettuce subscribe <repo-path> \
  --remote <remote-repo-or-url> \
  --stream <remote-stream> \
  --local-stream streams/shared/<name> \
  --commit
```

If shared-stream pulls are part of the runtime flow, summarize what was mirrored and what policy boundary applies.

## When Not To Use Lettuce

Do not use Lettuce when:

- the request is personal memory, family, health, legal, or unrelated to the scoped org/project;
- the operator wants a one-off answer that does not need durable work context;
- the runtime does not actually have permission to access the external source yet;
- using Lettuce would duplicate a chat, email, browser, or OAuth surface the runtime already owns;
- the operator asked not to store the signal durably;
- the signal belongs in a different org-scoped Lettuce.

When skipping Lettuce, say so briefly and continue the task without creating misleading durable state.

## Ongoing-Use Smoke Scenario

After setup, the operator says:

```text
Run Lettuce on this: customer says pricing is unclear and they think enterprise SSO should be standard.
```

Agent behavior:

1. Identify the correct org-scoped repo.
2. Write the signal to a temporary markdown file.
3. Ingest it as direct input with provenance.
4. Run handlers behind review.
5. Summarize the result and ask approve, edit, or decline.

Example commands:

```bash
cat > /tmp/lettuce-followup-signal.md <<'EOF'
Customer says pricing is unclear and they think enterprise SSO should be standard.
EOF

lettuce ingest-direct <repo-path> \
  --title "Customer pricing feedback" \
  --body-file /tmp/lettuce-followup-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --commit
lettuce run <repo-path> --review --commit
lettuce reviews <repo-path>
```

Expected handoff summary:

```text
I captured the signal in <repo-path> with direct-input provenance, ran the active handlers, and generated <n> review proposal(s). Nothing was written durably to brain streams yet. Approve, edit, or decline these updates. Manual/direct ingestion remains the trigger for ad hoc use; recurring source checks are <configured cadence or manual only>.
```

## Minimal Handoff Template

For any ongoing-use run, end with:

- repo/org scope used;
- whether you looked up existing context first;
- what signal or source was ingested or updated;
- whether review proposals were created, approved, edited, or declined;
- whether any recurring cadence or shared-stream contract changed;
- the next useful trigger or setup step.
