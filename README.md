# Lettuce

**Distributed company context for agents, built on markdown and git.**

Lettuce gives an operator's agent a durable work brain for one company, client, or project. Instead of relying only on chat history, personal memory, or a centralized all-seeing company brain, the agent can turn selected work signal into reviewed, provenance-backed context that lives in a repo the operator owns.

The v0 shape is intentionally simple:

```text
source signal -> stream event -> handler/lens -> optional review -> brain update -> git history
```

A customer email, call note, Telegram message, support transcript, or local file becomes a markdown event with provenance. Markdown handlers decide what matters. The result is a durable context update your agent can use later, inspect, review, revise, and share deliberately.


## Status: early public v0

Lettuce is ready for builders to inspect, clone, and dogfood as a local-first protocol/CLI for agent-owned company context. It is not a finished collaboration platform or hosted company brain.

Use it today if you are comfortable with markdown, git, local CLI tools, and agent-operated workflows. Treat it as a concrete protocol loop for turning selected work signal into reviewed context, not as a turnkey enterprise knowledge system.

The first real dogfood use is Ken + Soren using Lettuce to make agent work more durable and reviewable. That dogfood has already shaped the v0: streams, handlers/lenses, review gates, provenance, checkpoints, logs, and git history are the core product, not a dashboard veneer.

Current public posture:

- **Good for:** local-first dogfooding, founder/operator experiments, agent workflow research, markdown+git context protocols, and small reviewable company/project brains.
- **Not yet:** hosted multi-tenant SaaS, polished team UI, remote shared-stream sync, enterprise permissions, or automatic ingestion from every tool.
- **Safety model:** selected signal in, provenance preserved, optional review before brain updates, git history for audit/revert, and operator-owned repos rather than an all-seeing central system.

## Why this exists

Agents are becoming good enough to help run real work, but their context is usually fragile:

- chat memory goes stale or disappears across sessions;
- personal assistant memory gets mixed with company/project truth;
- generic knowledge bases preserve documents, not judgment;
- centralized company-brain tools often want every inbox, transcript, and permission surface in one place;
- downstream agents can act on stale or disputed context without a clear review trail.

Lettuce takes a narrower path: keep company context local-first, repo-owned, explicit, reviewable, and eventually distributed across bounded operator and role-agent repos.

## What you can do today

Current status: **early public v0 protocol loop**.

The installable `lettuce` CLI can:

- scaffold a markdown+git Lettuce repo;
- ingest direct, email-shaped, file, directory, and stdin signals as stream events;
- run markdown handlers through a local deterministic adapter for protocol smoke tests;
- write proposed or accepted brain updates;
- record provenance, checkpoints, logs, reviews, and setup handoffs;
- keep first setup lightweight for a solo founder while recording optional multi-operator/shared-stream intent.

The operator's agent is the runtime. Lettuce does **not** own chat surfaces, inboxes, OAuth grants, browser sessions, service integrations, model judgment, or scheduling. The agent runtime owns access and judgment, then writes selected signal and reviewed updates into Lettuce with provenance.

Not shipped yet: real remote shared-stream pulling, checkpointed git mirroring, a built-in `pull-subscriptions` command, hosted dashboards, team permissions, or turnkey integrations.

## Give this to your agent

Give your agent this one link:

```text
https://raw.githubusercontent.com/kenseals/lettuce/main/llms.txt
```

That file tells the agent what Lettuce is, what to install, which docs matter, and how to guide first setup without making you learn the CLI first.

If your agent prefers an install-runbook style prompt, paste this instead:

```text
Retrieve and follow the instructions at:
https://raw.githubusercontent.com/kenseals/lettuce/main/INSTALL_FOR_AGENTS.md
```

The intended operator experience is: answer setup questions, approve boundaries, and let the agent run the helper commands if it has tool access.

## Try the first local loop

Install from GitHub:

```bash
python3 -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

If your shell cannot find the installed `lettuce` script because the user Python bin directory is not on `PATH`, use `python3 -m lettuce.cli ...` for the same commands. For local development from a cloned repo, use `python3 -m pip install .`; for editable installs, upgrade pip first, then run `python3 -m pip install -e .`.

Run one demo signal through the loop:

```bash
printf 'Customer says agent context is stale.\n' > /tmp/lettuce-first-signal.md
lettuce onboard ./lettuce-demo --org demo --operator you --title "Demo signal" --body-file /tmp/lettuce-first-signal.md --source openclaw.telegram --surface telegram --consent operator-direct-request --review --commit
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
```

That scaffolds an org-scoped Lettuce repo, writes the first event to `streams/inbox/direct`, records `onboarding/setup/handoff.json`, writes review artifacts/state, records checkpoints/logs under `.lettuce/`, and commits changes to git when `--commit` is set.

Add `--review` when you want calibration or human approval before brain updates land. First agent-operated onboarding should usually use review mode.

For the shortest guided path, see `TRY_THIS_FIRST.md`. For a public-safe walkthrough, see `docs/first-run-demo.md`.

## How Lettuce works

### 1. Streams preserve selected signal

Streams are repo folders that hold timestamped markdown events. A direct chat input might land under `streams/inbox/direct`; an operator-forwarded email might land under `streams/inbox/email`; shared company decisions can later be exported under `streams/shared/*`.

Each event keeps provenance: where it came from, who forwarded or approved it, and what consent/boundary applied.

### 2. Handlers interpret what matters

Handlers are markdown files with YAML frontmatter and a prompt body. They subscribe to streams, read events, and publish structured outputs.

Lettuce uses three plain-English conventions:

- **Lenses** interpret messy signal into durable meaning.
- **Routers** decide where interpreted signal should go or what downstream action should be prepared.
- **Handlers** are the general primitive for anything else: summarizers, fact-checkers, fan-outs, evaluators, maintenance checks.

The runtime treats them the same; the names are for human and agent legibility.

### 3. Review gates prevent silent brain drift

A handler can publish directly, but the safer first setup is review mode: handler outputs become pending review proposals before they update `brain/*`.

That matters because company context is not just storage. It is judgment. Lettuce is designed so an operator or agent can inspect why a fact, decision, customer insight, or route was promoted.

### 4. Git makes the context portable and auditable

Because the state is markdown in git, it can be diffed, branched, reverted, reviewed in PRs, copied across runtimes, and inspected without a proprietary dashboard.

## Handlers: lenses and routers in practice

Handlers are the most important primitive in Lettuce. They turn “we have a pile of inputs” into “the agent knows what changed and what to do next.”

Example lenses:

- **Customer pain lens**: reads calls, emails, and chats; publishes recurring pains, objections, exact customer language, and evidence into `brain/customers`.
- **Decision lens**: watches meeting notes and operator messages; extracts accepted decisions, owners, effective dates, and supersession/conflict metadata into `brain/decisions` or shared decision streams.
- **Risk lens**: scans support tickets or incidents; promotes only durable risks, open questions, and follow-up owners instead of dumping every log line.
- **Market signal lens**: reads curated articles or research notes; records only the market shifts that should change product or positioning.

Example routers:

- **Linear router**: reads reviewed product/customer context and prepares issue candidates only when the evidence clears a threshold.
- **Founder briefing router**: turns recent brain updates into a concise operator handoff for the next morning or next work block.
- **Sales follow-up router**: notices buying intent or unresolved objections and drafts follow-up tasks without sending anything automatically.
- **Role-agent router**: routes selected context to a support-agent or sales-agent Lettuce without giving that role agent every raw source.

A minimal handler is just markdown:

```markdown
---
id: customer-pain-lens
name: Customer Pain Lens
type: lens
version: 0.1.0
subscribes:
  - stream: streams/inbox/direct
publishes:
  - stream: brain/customers
    mode: append
---

Read the event. If it contains durable customer pain, publish a concise brain entry with:
- the pain in the customer's words
- why it matters
- source evidence
- suggested follow-up, if any

If there is no durable customer signal, return {"skip": true}.
```

For the full handler format, see `HANDLERS.md`.

## Signal sources

Direct input from Telegram, iMessage, Discord, CLI, web chat, or any other operator surface should arrive through the operator's agent, then be written as a stream event with provenance such as `source: openclaw.telegram`. Lettuce should not build duplicate chat surfaces when the agent already owns them.

For later direct input the agent already received:

```bash
lettuce ingest-direct ./lettuce-demo \
  --title "Customer signal" \
  --body-file /tmp/customer-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --commit
lettuce run ./lettuce-demo --review --commit
```

For operator-selected or forwarded emails, keep the event email-shaped:

```bash
lettuce ingest-email ./lettuce-demo \
  --subject "Codex Product Update" \
  --body-file /tmp/lettuce-forwarded-email.md \
  --message-id <message-id> \
  --thread-id <thread-id> \
  --from "Sender <sender@example.com>" \
  --forwarded-by you \
  --consent operator-forwarded-email \
  --commit
```

The first repeatable source connector is deliberately local and boring: `add-source directory --input <dir>` imports a sample of new `.md`/`.txt` files into stream events, preserves file provenance and consent, and checkpoints imported file versions so later runs only pick up new or changed files. `add-source file` imports one local text/markdown file, and `add-source stdin` does the same for piped or supplied text.

`add-source email|fathom|granola|transcript|zoom` records repo-owned source configuration intent under `sources/` and creates the target stream directory. These records can include `access_status`, `sample_policy`, `privacy_notes`, and `setup_next_action`, so the operator's agent can see whether it can sample now or needs to guide setup first.

`lettuce onboard` can create or reuse those same records and reference them from `onboarding/setup/handoff.json` along with cadence/trigger hints and first-sample outcome. It does not pretend to provision forwarding addresses, OAuth, or webhooks by itself; agent-owned setup can attach to the same source record later.

## Distributed context and optional hubs

Lettuce is designed for distributed company context rather than one centralized brain that sees everything.

The default path is one personal/operator Lettuce repo for one company or project. That repo can stay private and local-first. If the organization later has multiple operators or role agents, each can have its own bounded Lettuce repo with its own GitHub identity and source access.

An org can also keep an optional `company_hub` Lettuce repo as a lightweight coordination point for curated shared context.

Use the hub for:

- exported shared streams under `streams/shared/*`;
- accepted company decisions and durable facts;
- discovery metadata for shared streams;
- stream owners and policy notes.

Do not use the hub for:

- every operator's raw inbox or transcripts;
- direct remote writes into `brain/*`;
- a centralized all-seeing company dump.

Shared pulls and mirrors may only write under `streams/shared/*`. GitHub access remains the outer boundary; Lettuce export and path policy narrows what gets shared inside that boundary.

`subscribe` records remote/shared stream subscription intent under `subscriptions/`. Shipped today: export declarations in `lettuce.yml`, subscription records, local-path export-policy checks, and local mirror-path/policy validation so subscriptions stay scoped to `streams/shared/*`. Not shipped yet: a real `pull-subscriptions` mirror command, remote polling, or checkpointed git mirroring.

When a repo declares `exports` in `lettuce.yml`, it is intentionally marking specific `streams/shared/*` paths as shareable. Those export declarations are editorial metadata for agents and runtime checks; they never grant access beyond the underlying GitHub repo permissions.

`lettuce init --repo-type company_hub` scaffolds the optional hub convention with default shared exports and starter directories for:

- `streams/shared/decisions`
- `streams/shared/customers`
- `streams/shared/incidents`
- `streams/shared/projects`

Hub-level accepted decisions and facts should use explicit metadata for status, supersession, ownership, timing, evidence, and confidence:

```yaml
status: active # active | superseded | disputed | draft
decision_owner: sarah
supersedes: previous-event-id
effective_at: 2026-05-04T00:00:00Z
source_events:
  - github.com/acme/lettuce-acme-ken:streams/shared/customers/event.md
confidence: medium
```

If company truth changes or becomes contested, append a new entry with updated metadata rather than silently overwriting the older accepted entry.

## Solo founder vs multi-operator setup

Use the default `solo_founder` onboarding path unless the operator explicitly needs multi-operator coordination later. That keeps first setup simple: personal Lettuce repo, manual/direct signal, one source plan, first handler pass, and optional GitHub remote next.

If the org already has multiple operators or role agents, `lettuce onboard ... --onboarding-path multi_operator` records that branch in `onboarding/setup/handoff.json` together with intent for personal/role-agent/hub repo discovery and future shared-stream coordination. It does not claim that remote mirroring or `pull-subscriptions` already ship.

## Minimal maintenance loop

Lettuce v0 does not run its own daemon. The external runtime or cron decides when to check, then calls existing commands such as `lettuce status`, `lettuce ingest-*`, `lettuce run --review`, and `lettuce reviews`.

`lettuce status` includes repo identity metadata and a small `freshness` summary so the agent can tell whether a repo is owned by a `human_operator` or a `role_agent`, whether it is `fresh`, `pending_review`, `blocked_on_setup`, or `idle_manual_only`, and which maintenance modes are configured: `manual`, `after-meeting`, `daily`, `source-check`, and `subscription-pull`. That last mode currently expresses subscription maintenance intent; it does not mean a built-in pull command already exists.

Role-agent repos are first-class Lettuce repos, not hidden company-hub special cases. Use names such as `lettuce-acme-support-agent`, keep them `private` by default, and set `permission_basis` to the bounded GitHub identity that owns the repo access: `github-app`, `machine-user`, or `github-user`. A role agent should inherit only that identity's permitted scope, not become an all-seeing org brain.

## Agent-Operated Runtime Contract

The primary Lettuce path is agent-operated:

1. The operator's agent receives the signal through its existing runtime: chat, email, browser, transcript, file, or work-system tools.
2. The agent reads the relevant Lettuce source records and lenses.
3. The agent uses its own model judgment to decide what matters, what changed, what not to do, and which review/update route applies.
4. Lettuce CLI helpers do deterministic work: ingest events, preserve provenance, list/audit routes, create/review/apply markdown artifacts, update checkpoints, and keep git history inspectable.

In other words: Lettuce is not a second agent runtime. It is the repo-backed protocol/state layer the runtime operates against.

## Handler Execution

Handler execution is pluggable through `LETTUCE_HANDLER_COMMAND`, but this is a compatibility and smoke-test seam, not the preferred OpenClaw path. If it is unset, the local protocol loop invokes the bundled deterministic adapter with the same stdin/stdout JSON contract, so file, stream, checkpoint, review, and git behavior can be tested without blocking on model credentials.

An older experimental adapter can call a local OpenClaw model command:

```bash
LETTUCE_HANDLER_COMMAND="python3 -m lettuce.openclaw_provider" \
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
lettuce run ./lettuce-demo --commit
```

That adapter is intentionally optional and should not be confused with the product architecture. In OpenClaw, the agent should normally run the lens judgment directly and use Lettuce helpers for durable protocol/state operations. The command adapter remains useful for CLI-only experiments, compatibility testing, or runtimes that intentionally expose model calls through a subprocess interface.

## What Lettuce is not

- not a generic notes app
- not a vector memory store
- not a company brain by itself
- not a dashboard-first product
- not a replacement agent/runtime
- not a first-party chat adapter, inbox provider, OAuth broker, or scheduler
- not an all-seeing centralized company dump

The core idea is **lenses before routers**: decide what matters and where it should go before downstream agents act.

## Docs map

Start here:

- `TRY_THIS_FIRST.md` — shortest usable smoke path.
- `docs/company-context-for-agents.md` — product frame and boundaries.
- `docs/first-run-demo.md` — public-safe first-run walkthrough.
- `INSTALL_FOR_AGENTS.md` — linear setup guide for agents.
- `docs/agent-operated-onboarding.md` — full agent-operated onboarding contract.

Protocol and operations:

- `LETTUCE_V0_SPEC.md` — v0 protocol source.
- `HANDLERS.md` — handler format and execution contract.
- `QUICKSTART.md` — full local walkthrough.
- `docs/trust-boundary.md` — local/runtime/shared trust model.
- `docs/LETTUCE_VERIFY.md` — post-setup verification.
- `docs/LETTUCE_RESOLVER.md` — ongoing agent use after setup.
- `docs/source-discovery-recipes.md` and `docs/source-recipes/` — source setup decisions and recipes.
- `docs/openclaw-runtime-source-setup.md` — OpenClaw source setup contract.
- `skills/openclaw-lettuce/SKILL.md` — repo-packaged OpenClaw skill.

Launch/reference:

- `docs/public-v0-launch-note.md`
- `docs/public-v0-release-checklist.md`

## Tests

```bash
python3 -m unittest discover -s tests
python3 -m py_compile lettuce/*.py
python3 -m lettuce.runtime --smoke
```
