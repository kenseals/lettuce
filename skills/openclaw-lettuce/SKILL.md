---
name: openclaw-lettuce
description: Use when an operator asks an OpenClaw agent to set up, run, dogfood, or operate a Lettuce implementation for an organization or project. Covers onboarding, direct signal ingestion, source discovery, handler runs, and the inspect/adjust optional review mode.
---

# OpenClaw Lettuce

Lettuce is an agent-operated markdown+git protocol. OpenClaw is the runtime in v0: it owns conversation surfaces, tool access, identity, auth, and setup guidance. Lettuce owns durable state: repo, streams, handlers, brain entries, source records, subscriptions, checkpoints, logs, and optional review conventions.

Do not build duplicate chat surfaces for direct input. If the operator is talking to OpenClaw through Telegram, iMessage, Discord, CLI, or another surface, OpenClaw already owns that surface. Write selected direct input into Lettuce with provenance.

## When To Use

Use this skill when the operator asks to:

- set up Lettuce for an org/project
- run Lettuce onboarding
- ingest a direct signal into Lettuce
- add or discover signal sources
- run handlers and inspect brain outputs
- inspect Lettuce status/logs
- tune handlers/lenses/routers

## Required Repo Context

The Lettuce repo should contain:

- `LETTUCE_V0_SPEC.md` for the protocol spec
- `HANDLERS.md` for markdown handler format
- `docs/agent-operated-onboarding.md` for setup flow
- `docs/source-discovery-recipes.md` for source setup decisions
- `QUICKSTART.md` for local CLI smoke path

Read only the specific file needed for the task.

## Onboarding Flow

When setting up a new Lettuce, do not silently install/init/ingest. First explain the product in one short paragraph:

```text
Lettuce gives your agent a local markdown+git work brain for one company/project. It keeps work context separate from personal memory, records which sources should feed that context, and lets me keep useful company context fresh from signals I can access. The point is not to make you review every signal; it is to give me durable work context I can use later.
```

Then ask/confirm the setup inputs:

- org/project name or slug
- operator handle/name
- repo path or whether to start locally first
- signal sources that should eventually feed this Lettuce
- sources that are available now vs need setup/defer
- cadence or trigger model for keeping context fresh
- first meaningful direct signal to ingest, if not already in the conversation
- consent basis for ingesting that first signal

If the context seems obvious, state it as an assumption and wait for confirmation. Do not use the setup request itself as the first signal unless the operator explicitly says to; it tends to create vague setup-context reviews.

Then run the helper:

```bash
lettuce onboard <repo-path> \
  --org <org> \
  --operator <operator> \
  --title "<first signal title>" \
  --body "<first signal body>" \
  --source "openclaw.telegram" \
  --surface "telegram" \
  --sender "<operator>" \
  --consent "operator-direct-request" \
  --openclaw-provider \
  --commit
```

Use the actual source/surface available in the inbound context. Examples: `openclaw.telegram`, `openclaw.imessage`, `discord`, `cli`, `browser-chat`.

Use `--openclaw-provider` when OpenClaw's local model command is available; it avoids the deterministic fallback that only proves plumbing. Omit it only for offline smoke tests.

After running, summarize the JSON result in operator language:

- repo initialized or reused
- event path and source provenance
- handlers that ran
- brain updates written, with a plain-English explanation of what each added and why it matters
- skipped handlers/errors/noisy output
- current checkpoints/log count
- configured source records and whether each is available now, needs setup, or deferred
- whether there is any recurring schedule; if none, say new signals are manual/agent-triggered for now

If something looks wrong, offer to edit or revert the git commit. Do not turn normal operation into a standing approval queue.

Then give a final onboarding handoff: repo path, scoped org/project, source plan, current trigger/schedule model, what was added or skipped, and the next useful source setup step.

## Direct Signal Ingestion

For later direct input after onboarding:

```bash
lettuce ingest-direct <repo-path> \
  --title "<signal title>" \
  --body "<signal body>" \
  --source "<agent.surface>" \
  --surface "<surface>" \
  --message-id "<id-if-known>" \
  --sender "<operator-or-sender>" \
  --consent "<basis>" \
  --commit

lettuce run <repo-path> --commit
lettuce status <repo-path>
lettuce logs <repo-path> --limit 5
```

Preserve provenance when available: source, surface, message id, thread/chat/topic id, sender, observed timestamp, and consent/standing-rule basis.

For operator-forwarded or selected emails, use `ingest-email` instead of flattening the event into direct chat input:

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

## Source Discovery

For email, transcripts, and work systems, inspect existing OpenClaw access first. Do not ask the operator for setup until a source is clearly useful and unavailable.

Use this classification:

- `available_now`: OpenClaw already has connector/API/MCP/browser/file access and can sample.
- `needs_setup`: the operator must connect OAuth, forwarding, export, webhook, MCP, or provide credentials/files.
- `defer`: useful later, not needed for the first working Lettuce.

Always sample small first, usually 1-5 items, then inspect outputs before bulk backfill.

When a source will recur, record durable source intent:

```bash
lettuce add-source email <repo-path> --name <name> --address <mailbox-or-account> --access-status available_now --sample-policy first-5-operator-approved --commit
lettuce add-source granola <repo-path> --name <name> --workspace <workspace> --access-status needs_setup --setup-next-action "connect existing export or MCP before polling" --commit
```

Use source records as agent-readable setup/status contracts: what access exists, what small sample is allowed, what privacy boundary applies, and what setup action remains. Transcript-oriented records include `fathom`, `granola`, `zoom`, and generic `transcript`.

## Handler Runs

Run handlers with:

```bash
lettuce run <repo-path> --commit
```

The command prints handler progress to stderr and returns machine-readable JSON on stdout. In OpenClaw, prefer `lettuce run --openclaw-provider <repo-path> --commit` for real judgment. Brain updates land in `brain/*` by default with provenance and git history. Use optional `--review` only for sensitive sources, calibration, high-impact changes, or explicit operator approval gates. If model-backed handlers are slow, use `LETTUCE_HANDLER_TIMEOUT_SECONDS` to cap each handler command.

## Safety Rules

- Do not exfiltrate private data into a Lettuce repo.
- Do not ingest personal-life context into an org-scoped Lettuce.
- Do not bulk-ingest before a small inspected sample.
- Do not create OAuth/webhook/bot infrastructure when OpenClaw already has access or direct input.
- Do not apply external writes without explicit approval or a standing rule.
- Prefer git commits for reversible checkpoints.

## Success Criteria

A good first setup ends with:

- `lettuce.yml` created
- default handlers discovered
- one direct signal ingested with provenance
- handlers run successfully
- at least one brain update written or a clear skip reason logged
- source plan captured
- checkpoints/logs present
- operator understands where the repo lives and how new signals will flow
