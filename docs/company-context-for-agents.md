# Company Context for Agents

Lettuce exists because agents are becoming the way operators do work, but most agents still have no durable, portable, org-scoped place to keep company context.

The next version of high-leverage work is not just one assistant answering questions. It is operators and teams managing small fleets of agents across coding, research, support, GTM, and operations. Those fleets need orchestration, task graphs, guardrails, and coordination, but they also need something more basic: a scoped, inspectable, versioned place where company context can compound without bleeding across roles or tools.

An operator can have one agent and many hats: a day job, a side project, a client, a nonprofit board, a personal life. Those contexts should not bleed together.

Lettuce gives the agent a separate work brain per organization.

It is also becoming the agent's **context and connector control plane** for that organization. Not just memory, and not just integrations: Lettuce records what systems feed context in, which handlers interpret that signal, what company context has been accepted, and eventually which destinations can be safely updated.

## The promise

For each `(operator, org)` pair, Lettuce provides:

- a git repo owned by the operator;
- markdown streams for work signal;
- markdown brain entries for durable company context;
- markdown handlers/lenses that define what the agent should notice;
- provenance and git history for durable context changes;
- checkpoints/logs so runs are reconstructable;
- subscription records so separate Lettuces can later exchange scoped streams.

The agent runtime, OpenClaw in v0, owns conversation, tools, source access, auth, browser sessions, and scheduling. Lettuce owns the durable protocol the agent uses once it has signal.

## Connectors, sources, and destinations

Use this product language carefully:

- **Connector**: an external system relationship the agent runtime can use for this org.
- **Source**: an inbound connector that brings signal into Lettuce, such as email, transcripts, GitHub issues, Linear, Slack, docs, files, or direct/manual operator input.
- **Destination** or **surface**: an outbound connector where accepted context or approved actions may go later, such as Linear issues, GitHub comments, docs, CRM, support tools, Slack, or roadmap/task systems.
- **Bidirectional connector**: a system like GitHub, Linear, Slack, or docs that can both emit useful signal and receive approved updates.

For v0, keep the repo protocol concrete: `sources/*` are inbound source records, `handlers/*` interpret streams, `brain/*` stores accepted context, and review records gate uncertain or sensitive updates. Do not prematurely rename the protocol around a broad connector abstraction.

But the broader product direction is important: Lettuce should help the operator and agent see, in one place, which connectors exist, what readiness state they are in, what handlers run over their signal, what context has been accepted, and what outward surfaces are safe to update.

Example:

- GitHub as a **source**: issues, PRs, comments, releases, and review outcomes can become signal.
- GitHub as a **destination**: approved context may create/comment/update an issue or PR note.
- Lettuce's job is not to own GitHub auth or webhook plumbing. The runtime owns that. Lettuce owns the durable contract, provenance, review/freshness state, and the rules that prevent the agent from treating access as permission to ingest or write everything.

## Why not just agent memory?

General agent memory is convenient but blurry.

Company context needs different properties:

- **Scoped:** Acme context should not mix with personal life or another client.
- **Portable:** the operator should not lose work context when switching agent runtimes.
- **Inspectable:** humans should be able to read and edit the context directly.
- **Versioned:** every durable change should be reversible through git.
- **Reversible:** the agent should not make unrecoverable changes to company truth.
- **Shareable:** teams need scoped streams between agents, not one giant centralized ingest bucket.

## Current public-v0 loop

Public v0 proves the smallest recognizable version:

```text
operator/agent observes work signal
        ↓
agent writes org-scoped stream event
        ↓
Lettuce handlers interpret the signal
        ↓
useful updates become markdown brain entries
        ↓
updates are committed with provenance and checkpoints
        ↓
operator can inspect, edit, revert, or optionally require review for sensitive flows
```

This is not the whole company-context system yet. It is the control loop that makes the larger system concrete enough to improve.

## What the agent runtime owns

The runtime connects to the world:

- Telegram, iMessage, Discord, CLI, or browser chat;
- email and forwarded messages;
- transcript tools and exported files;
- GitHub, Linear, Notion, Slack, and other work systems;
- polling, browser automation, OAuth, API keys, MCP servers, and local files.

Lettuce should not duplicate those surfaces. Instead, it teaches the runtime how to preserve provenance and turn selected signal into durable org-scoped context.

## What Lettuce owns

Lettuce owns the protocol shape:

- repo structure;
- `lettuce.yml` marker/config;
- streams;
- handlers;
- brain directories;
- source records;
- subscription records;
- optional review records;
- checkpoints;
- logs;
- apply/decline rules.

Everything important is markdown or git state.

## Distributed company context

The longer-term company version is not one centralized company brain that ingests everything.

It is a set of operator-owned Lettuces, each reflecting what that operator and agent can actually see. Agents can prepare to subscribe to shared streams when useful and permitted.

A teammate's agent might publish a scoped customer update. Your agent should eventually be able to subscribe to that stream, decide what matters for your work, and update your org-scoped brain without seeing your teammate's entire inbox or personal memory.

That is the eventual distributed-context shape:

```text
operator A's agent + Lettuce ──shared stream──▶ operator B's agent + Lettuce
         │                                           │
         └── owned personal work repo                └── owned personal work repo
```

GitHub permissions and runtime access remain the outer boundary. Lettuce policies, provenance, git history, and optional review modes add narrower control.

An org may also keep an optional `company_hub` repo as a coordination point for curated shared streams and accepted org-level truth. The hub is not a replacement for operator-owned repos. It should hold exported shared context, discovery metadata, and owner/policy notes, while avoiding raw inbox/transcript dumps by default.

Today that shared-stream story is only partially shipped: export declarations, subscription records, local export-policy checks, and repo identity scaffolding exist; real pull/mirror execution and broader policy verification are still roadmap work. See roadmap issues `#20`, `#35`, `#36`, `#37`, and `#38`.

Accepted company-hub truth should carry explicit status metadata so agents can reason about conflicts and freshness:

```yaml
status: active # active | superseded | disputed | draft
decision_owner: sarah
supersedes: previous-event-id
effective_at: 2026-05-04T00:00:00Z
source_events:
  - github.com/acme/lettuce-acme-ken:streams/shared/customers/event.md
confidence: medium
```

Do not silently overwrite disputed or superseded company truth in place. Publish a new event with explicit `status` and `supersedes` metadata so the older entry remains visible.

## What v0 is honest about

Working now:

- installable CLI;
- repo scaffold;
- direct/file/email-shaped event ingestion helpers;
- source intent records;
- markdown handlers;
- deterministic handler execution plus optional subprocess-backed provider execution;
- direct brain updates with provenance;
- optional review/approve/decline lifecycle;
- markdown brain updates;
- git commits;
- local tests and CI.

Still future or in progress:

- real recurring source polling;
- real Linear side effects;
- shared-stream pull/mirror execution;
- remote stream polling;
- broader policy enforcement for shared repos;
- org discovery;
- polished multi-agent setup flow.

The public-v0 promise should be narrow but true: Lettuce is the first working protocol loop for operator-owned company context for agents.
