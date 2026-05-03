# Company Context for Agents

Lettuce exists because agents are becoming the way operators do work, but most agents still have no durable, portable, org-scoped place to keep company context.

An operator can have one agent and many hats: a day job, a side project, a client, a nonprofit board, a personal life. Those contexts should not bleed together.

Lettuce gives the agent a separate work brain per organization.

## The promise

For each `(operator, org)` pair, Lettuce provides:

- a git repo owned by the operator;
- markdown streams for work signal;
- markdown brain entries for durable company context;
- markdown handlers/lenses that define what the agent should notice;
- review gates before durable context changes;
- checkpoints/logs so runs are reconstructable;
- subscription records so separate Lettuces can eventually exchange scoped streams.

The agent runtime, OpenClaw in v0, owns conversation, tools, source access, auth, browser sessions, and scheduling. Lettuce owns the durable protocol the agent uses once it has signal.

## Why not just agent memory?

General agent memory is convenient but blurry.

Company context needs different properties:

- **Scoped:** Acme context should not mix with personal life or another client.
- **Portable:** the operator should not lose work context when switching agent runtimes.
- **Inspectable:** humans should be able to read and edit the context directly.
- **Versioned:** every durable change should be reversible through git.
- **Reviewable:** the agent should not silently rewrite company truth.
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
review proposals are written to reviews/pending
        ↓
operator/agent approves, edits, or declines
        ↓
approved updates become markdown brain entries committed to git
```

This is not the whole company-context system yet. It is the control loop that makes the larger system safe enough to build.

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
- reviews;
- checkpoints;
- logs;
- apply/decline rules.

Everything important is markdown or git state.

## Distributed company context

The longer-term company version is not one centralized company brain that ingests everything.

It is a set of operator-owned Lettuces, each mirroring what that operator and agent can actually see. Agents can subscribe to shared streams when useful and permitted.

A teammate's agent might publish a scoped customer update. Your agent can subscribe to that stream, review what matters for your work, and update your org-scoped brain without seeing your teammate's entire inbox or personal memory.

That is the eventual distributed-context shape:

```text
operator A's agent + Lettuce ──shared stream──▶ operator B's agent + Lettuce
         │                                           │
         └── owned personal work repo                └── owned personal work repo
```

GitHub permissions and runtime access remain the outer boundary. Lettuce policies and review gates add narrower editorial control.

## What v0 is honest about

Working now:

- installable CLI;
- repo scaffold;
- direct/file/email-shaped event ingestion helpers;
- source intent records;
- markdown handlers;
- deterministic and OpenClaw-backed handler execution;
- pending review proposals;
- approve/decline lifecycle;
- markdown brain updates;
- git commits;
- local tests and CI.

Still future or in progress:

- real recurring source polling;
- real Linear side effects;
- remote stream polling;
- policy enforcement for shared repos;
- org discovery;
- polished multi-agent setup flow.

The public-v0 promise should be narrow but true: Lettuce is the first working protocol loop for operator-owned company context for agents.
