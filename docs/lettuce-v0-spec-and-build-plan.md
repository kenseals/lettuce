# Lettuce v0 — Specification & Build Plan

> A self-contained document for an agent to read, internalize, and build v0 from. Contains the vision, the architecture, the protocol details, the user experience, the build plan, and the principles that should guide implementation decisions when this document is silent.

**Read this document end to end before writing any code.** The vision and principles sections inform decisions throughout the build, not just the chapters they appear in.

---

## Part 1: Vision

### 1.1 What Lettuce is

Lettuce is an open protocol for company context in the agentic era. It gives any operator's agent — whatever runtime it lives in — a structured, durable, portable layer of work-context that is owned by the operator, lives in their git repos, and is designed to later coordinate with teammates' Lettuces to form a coherent company-level intelligence layer without centralizing data.

The thesis: as everyone increasingly works through a personal agent, that agent needs a place to keep work-context that is (a) separable from personal life, (b) portable across agent vendors, (c) owned by the operator, not the platform, and (d) able to coordinate with the agents of teammates. Lettuce is that place.

The wedge: an individual operator running Lettuce gets immediate value — their agent now has structured context for their work, separable from their personal life. The compounding value: when teammates also run Lettuce, their agents can coordinate via shared streams without anyone having to centralize data.

### 1.2 Pronunciation and naming

The product is named **Lettuce**, pronounced *lattice* — a small joke on the structural meaning of "lattice" (interlocking layers, latticework, a framework holding things in place). The name is meant to be playful and memorable. The brand should earn the name without leaning on it crutch-like.

### 1.3 Core principles

These principles should guide implementation decisions when the spec is silent. They are ordered by precedence — earlier principles win when they conflict.

1. **Operator sovereignty.** The operator owns their data, their handlers, their interpretations. Lettuce never centralizes signal on servers it controls. The operator's brain is in the operator's repo, full stop.

2. **Inheritance over invention.** Use existing systems where possible. Permissions come from OAuth scopes and GitHub access controls, not a Lettuce IAM layer. Storage is git, not a custom datastore. Identity is whoever is authenticated to GitHub.

3. **Markdown legibility.** Everything an operator might want to read, edit, fork, or version-control is markdown — handlers, brain entries, stream events, policies. The runtime may maintain derived indexes for performance, but markdown is the canonical representation.

4. **Conversation over configuration.** Setup, troubleshooting, and ongoing interaction happen through conversation with the agent, not through wizards or config UIs. The agent narrates what it does and surfaces real decisions.

5. **Sensible defaults; reversible everywhere.** Every step has a default that works. Every default can be overridden. The operator can always edit, fork, or revert because everything is in git.

6. **Honest about scope.** v0 is a single-operator personal Lettuce that may optionally subscribe to shared company streams. Multi-operator coordination is *supported* by the protocol but not feature-spotlighted in v0. We ship the wedge first.

### 1.4 Vocabulary

Two layers of vocabulary, used deliberately:

**User-facing (warm, intuitive):**
- **Brain** — the operator's durable, structured work-context for an org.
- **Lenses** — handlers that interpret incoming signal.
- **Routers** — handlers that take interpreted signal and produce side effects in services.

**Protocol-level (precise, expressive):**
- **Handlers** — the unified primitive. Lenses and routers are types of handlers.
- **Streams** — durable or scoped logs of structured events. The brain is a stream.
- **Policies** — declarations about who can read/write each stream.

Both vocabularies are correct; documentation, marketing, and onboarding use the warm one. The protocol spec and developer documentation use the precise one. They map cleanly: a lens is a handler that subscribes to inbox streams and publishes to brain streams; a router is a handler that subscribes to brain streams and publishes to outbox streams or service APIs.

### 1.5 The value proposition

The product story has two parts: an immediate one (solo) and a compounding one (multi-operator). The compounding story is what makes Lettuce a venture-scale primitive; the solo story is what makes it useful from day one.

**Solo operator — keep work in its place.** Each Lettuce is scoped to one organization. *One agent, many hats — but no bleed between them.* Your context for Acme stays in your Acme Lettuce. Your context for your side project stays in its own Lettuce. Your personal life stays in your agent's general memory, untouched. One repo per `(operator × org)`. They never mix.

**Multi-operator — better with every teammate who installs it.** A solo Lettuce is useful from day one. The interesting thing happens when a teammate runs one too — and then a few more — and the company quietly accumulates a coordination layer no one had to centralize. The compounding story unfolds in three stages:

- **Stage 01 — Just you.** Your agent has structured work-context for one org. Useful immediately. *Unlocked: a personal company brain.*
- **Stage 02 — A teammate joins.** They install Lettuce too. The protocol is heading toward your agents subscribing to each other's shared streams. The customer your teammate's been talking to becomes visible to your agent — without anyone forwarding emails or copying notes. *Unlocked: cross-role context for free.*
- **Stage 03 — Your whole company.** A dozen agents, each mirroring their operator's actual access, eventually coordinating through shared streams governed by GitHub permissions and editorial policies. No one has to centralize. No one's agent ingests everything. *Unlocked: federated context for the whole org.*

Implementation note: v0 ships single-operator polished. Multi-operator coordination is supported by the protocol but not feature-spotlighted in v0 UX. The build sequence in part 4 reflects this: ship the single-operator wedge first, then layer in remote stream subscription and policy enforcement once the core loop is solid.

---

## Part 2: Architecture

### 2.1 The three primitives

**Handlers** are markdown files (with YAML frontmatter and a prompt body) that declare what they subscribe to, what they publish, and what they do. The runtime invokes them when their subscribed streams get new events. Lenses and routers are conventional types of handlers; the runtime treats all handler types identically.

**Streams** are git directories containing markdown event files. Publishing is a `git commit + push` of a new file. Subscribing is reading new files since a checkpoint. Three kinds of streams exist by convention:
- **Inbox streams** — incoming signal (email, transcripts, direct input), normalized.
- **Brain streams** — interpreted, durable context. Long retention (forever, in v0).
- **Outbox streams** — outbound events queued for service routers.

Streams may live in the operator's personal repo (local) or in shared company repos (remote). Public v0 fully ships the local path; remote/shared mirroring remains a planned next step.

**Policies** are markdown declarations within a stream's `lettuce.yml` that govern who can read and write to which stream paths. Policies augment GitHub's access control with editorial ownership rules. They never override GitHub permissions — they only further restrict.

### 2.2 Repository model

**One Lettuce per (operator × org) pair.** An operator working at one company has one Lettuce repo. An operator who advises three orgs has three. Each Lettuce is fully self-contained — handlers, brain, streams — in a single git repo.

**Personal Lettuce repo** (always exists):
```
lettuce-{org}-{operator}/
├── lettuce.yml          # config + marker file for discovery
├── handlers/
│   ├── lenses/
│   │   ├── default-lens.md
│   │   ├── discovery-lens.md
│   │   └── accounts-lens.md
│   └── routers/
│       ├── brain-router.md
│       └── linear-router.md
├── brain/               # the durable interpreted context
│   ├── customers/
│   ├── strategy/
│   ├── decisions/
│   └── ...
├── streams/
│   ├── inbox/
│   │   ├── email/
│   │   ├── transcripts/
│   │   └── direct/
│   └── outbox/
│       └── linear/
└── .lettuce/            # runtime state (checkpoints, logs)
    ├── checkpoints.json
    └── runtime.log
```

Lives in the operator's personal GitHub account by default. Private repo. Operator owns it.

**Shared company Lettuce repo** (optional, created by first operator with org-creation permission):
```
lettuce-{org}/
├── lettuce.yml          # marker + policies declaring which roles publish to what
├── brain/               # company-level shared brain (decisions, strategy, customers shared)
└── streams/
    └── ...              # cross-team shared streams
```

Lives in the company GitHub org. Permissions governed by the GitHub org's access controls plus the policies declared in `lettuce.yml`.

### 2.3 The `lettuce.yml` marker file

Every Lettuce repo has a `lettuce.yml` at root. This serves two purposes:

1. **Discovery marker.** When an agent scans a GitHub org for existing Lettuce installs, it looks for repos containing `lettuce.yml`.
2. **Configuration.** Declares the repo's metadata, policies, and (for shared repos) ownership/role rules.

Personal repo `lettuce.yml`:
```yaml
lettuce_version: 0.1.0
type: personal
operator: ken
org: acme
created_at: 2026-04-30T12:00:00Z
default_model: claude-sonnet-4
```

Shared repo `lettuce.yml`:
```yaml
lettuce_version: 0.1.0
type: shared
org: acme
created_at: 2026-04-15T09:00:00Z
admin_contact: sarah@acme.com
streams:
  brain/decisions:
    write_roles: [exec, lead]
    read_roles: [all]
    retention: forever
  brain/customers:
    write_roles: [sales, cs, exec]
    read_roles: [all]
    retention: forever
  streams/incidents:
    write_roles: [eng, sre]
    read_roles: [all]
    retention: 90d
```

The target shape is that the runtime reads `lettuce.yml` on subscribe and publish operations to enforce policy. Public v0 only partially ships this today: export declarations are parsed, subscription setup validates local-path remotes against explicit exports, and local mirror paths/policy strings are constrained under `streams/shared/*`. Full remote mirroring and broader policy enforcement remain roadmap work.

### 2.4 The runtime

The runtime is the agent (OpenClaw in v0) operating in a loop. Concretely:

1. **Initialization.** Read `lettuce.yml` from the operator's personal repo. Discover handlers in `handlers/`. In current v0, read any configured subscription intent records; later versions may also discover subscribed remote streams in shared company repos.
2. **Loop:**
   - Poll subscribed local sources for new events. Shared-stream polling is planned next, not part of the shipped v0 loop.
   - For each new event, find handlers subscribed to that stream.
   - For each matched handler, construct invocation, call LLM, parse output.
   - For each publish in the output, write the markdown file to the destination local stream and commit to git. Remote/shared mirroring is a later phase.
   - Update checkpoints.
3. **Trigger handling.** Schedule-triggered handlers run on cron. Manual-triggered handlers run when invoked by the operator or another handler.
4. **Logging.** All invocations, successes, failures, and publishes go to `.lettuce/runtime.log` in the operator's personal repo. Also surfaced in conversation with the operator on request.

In v0, the runtime is implemented as logic the agent (OpenClaw) executes — markdown handlers describing what to do, plus runtime convention describing how to do it. The agent is the orchestrator; the markdown is the program.

### 2.5 Permissions model

Three layers, listed top-to-bottom:

1. **Service permissions.** OAuth scopes for Gmail, Fathom, Linear, Slack, etc. The operator's agent only sees what the operator can see. No Lettuce-level service permission system — entirely inherited from OAuth.

2. **GitHub permissions.** Each Lettuce repo (personal or shared) has GitHub access controls. The runtime can only read/write to repos and paths the authenticated GitHub identity can access. No Lettuce-level GitHub permission system — entirely inherited.

3. **Editorial policies.** `lettuce.yml` declares ownership and write rules within streams. These augment GitHub permissions. The runtime enforces them at publish time. They never grant access GitHub denies; they only further restrict.

**Net effect for the implementer:** there is no permissions code to write beyond enforcing `lettuce.yml` policies at publish time. Everything else is OAuth and GitHub.

### 2.6 Stream events on disk

Each event is a markdown file in the destination stream's directory:

```
streams/inbox/email/2026-04-30T14-22-11Z-pricing-question-bigcorp.md
```

Filename: `<ISO-timestamp-with-hyphens>-<slugified-title>.md`. Hyphens instead of colons in timestamps for filesystem compatibility.

File contents — frontmatter (structured) + body (free text):
```markdown
---
id: 2026-04-30T14-22-11Z-pricing-question-bigcorp
timestamp: 2026-04-30T14:22:11Z
source: email
from: anna@bigcorp.com
subject: Quick question about pricing
thread_id: gmail-thread-abc123
---

Hi team, wanted to check if your enterprise tier...
```

Brain events have richer frontmatter:
```markdown
---
id: 2026-04-30T14-23-15Z-pricing-transparency-bigcorp
timestamp: 2026-04-30T14:23:15Z
handler: discovery-lens
handler_version: 0.1.0
source_event: 2026-04-30T14-22-11Z-pricing-question-bigcorp
title: Pricing transparency request from BigCorp
tags: [pricing, enterprise]
---

Anna at BigCorp asked about enterprise pricing...
```

### 2.7 Handler specification

See `HANDLERS.md` for the full handler spec. Summary: a handler is a markdown file with YAML frontmatter declaring `id`, `name`, `type` (`lens` | `router` | `handler`), `subscribes`, `publishes`, and triggers. The body is the LLM prompt. The runtime invokes handlers when subscribed streams get new events, passes events as structured JSON, parses handler JSON output, and writes publishes to destination streams.

---

## Part 3: User Experience

### 3.1 Onboarding flow

Onboarding happens through conversation between the operator and their agent. The agent is performing the install, but it does so as a guided conversation, not a silent script.

**Phase 1: Org anchoring**

The agent asks early which organization the Lettuce install is for. Even a solo founder gets asked — naming the org explicitly anchors all downstream defaults (repo name, signal source filtering, etc.).

> Agent: "Setting up Lettuce. Which organization is this for? You can run separate Lettuce installs for different orgs; let's start with one."

**Phase 2: Personal brain repo**

The agent walks the operator through creating their personal Lettuce repo. Two paths:

- **Agent creates it.** Operator grants GitHub OAuth with repo creation scope. Agent creates the repo, scaffolds the structure, commits the default handlers and an empty brain skeleton, and pushes to `main`.
- **Operator creates it manually.** Operator creates the repo themselves, gives the agent the URL, and the agent runs the bootstrapper to scaffold it.

Default repo name: `lettuce-{org}-{operator-handle}`. Operator can override.

**Phase 3: Company brain discovery**

Agent asks if a shared company brain already exists. Three branches:

- **Operator says yes, here's the URL.** Agent verifies access, reads the shared repo's `lettuce.yml` to understand exports/policies, and records subscription intent for relevant shared streams.
- **Operator says no / let's create one.** Agent checks if the operator has org-repo-creation permission. If yes, walks through creating the shared repo, with default `lettuce.yml` declaring the operator as initial admin contact. If no, explains the situation and offers to ping someone with permission.
- **Operator says I don't know.** Agent scans the company GitHub org for repos with `lettuce.yml` at root. If found, surfaces candidates. If not, offers to create one.

**Phase 4: Signal sources**

Agent walks through wiring up signal sources, one at a time, lowest-friction first:

1. **Direct input through the agent** — works immediately because the operator is already talking to their agent through some surface: Telegram, iMessage, Discord, CLI, web chat, or another channel. Lettuce does not need to own that surface; the agent writes selected direct input into a Lettuce stream with source/provenance metadata.
2. **Email** — the agent uses an email account or forwarding path it has access to, with operator consent, then writes relevant messages into Lettuce streams.
3. **Call transcripts** — the agent uses available APIs/MCP/OAuth for Fathom, Granola, Zoom, Otter, or similar, then writes relevant transcripts into Lettuce streams.

Each connection is a separate consent flow. Operator can skip any. The rule is: the agent owns access and communication surfaces; Lettuce owns the durable stream/handler/brain protocol.

**Phase 5: First run**

Once at least one signal source is connected, agent kicks off the first ingestion: pulls any historical signal it can (e.g., Fathom transcripts from the last 90 days), runs lenses against them, commits initial brain entries. Operator can watch this happen in conversation — agent narrates what it found.

End state: operator has a working Lettuce with at least one signal source flowing in, default lenses producing brain entries, and optionally recorded shared-stream subscription intent for later coordination. Total elapsed time: 5–15 minutes depending on source setup and how many signal sources they wire up.

### 3.2 Day-to-day UX

**The agent is the interface.** The operator interacts with Lettuce through conversation with their agent, not a separate UI. Common operations:

- "What does my brain say about BigCorp?" → agent reads brain, summarizes.
- "Add a fact-checker lens to my Lettuce." → agent walks through writing a new handler.
- "What did the discovery lens flag this week?" → agent queries `brain/discovery/` for recent entries.
- "Reset the discovery lens — it's been hallucinating." → agent rolls back the checkpoint, optionally reverts recent commits.

**The repo is the source of truth.** If the operator wants to read or edit anything directly, they can — it's a git repo full of markdown. The agent and the repo are two interfaces to the same state; they never drift apart.

### 3.3 Failure modes and how to surface them

The runtime should surface failures *loudly* but *constructively*. Examples:

- **OAuth grant expired:** "Your Fathom connection expired. Want me to re-authenticate now?"
- **Handler returned malformed JSON:** "The discovery-lens handler returned something I couldn't parse. The raw output is in `.lettuce/runtime.log`. Want me to skip this event or retry?"
- **Publish blocked by policy:** "Tried to publish to `acme/lettuce-brain:brain/decisions` but your role doesn't have write access there. Logged locally instead. Talk to Sarah if you need that access."
- **Signal source rate-limited:** "Hit Gmail's rate limit. Backing off for 10 minutes, will resume after."

The principle: no silent failures. Every failure is visible to the operator with enough context to understand and fix it.

---

## Part 4: PRD — What v0 Ships

### 4.1 Scope

v0 ships:

- A `lettuce` CLI tool installable in OpenClaw (or invokable by OpenClaw via shell). The shipped surface centers on `init`, `onboard`, `run`, `subscribe`, `status`, `logs`, review commands, and source-ingest/source-config helpers.
- A reference set of default handlers (3 lenses, 2 routers, 1 helper).
- A bootstrapper that scaffolds personal Lettuce repos with sensible defaults.
- Agent-operated ingestion from three source classes: direct input received through the agent's existing communication surfaces, email the agent can access, and call transcripts available through APIs/MCP/OAuth.
- Integration with one outbound service: Linear (via API).
- Single-operator setup as the spotlight UX. Multi-operator subscription intent works; actual shared-stream mirroring stays documented as "future direction" in user-facing copy.
- Documentation: README, HANDLERS.md (handler spec), QUICKSTART.md, CONTRIBUTING.md.
- A simple landing page (already drafted) at `lettuce.{tld}` linking to the GitHub repo and a 90-second demo Loom.

v0 does *not* ship:

- A hosted runtime. v0 is OpenClaw-only.
- Adapters for other agents (Claude Code, Codex, etc.) — these are v0.2.
- A web UI or admin dashboard. Everything is conversational + git.
- Multi-operator coordination as a polished feature. The protocol supports it; the UX doesn't yet spotlight it.
- Any analytics, telemetry, or observability features beyond local logs.

### 4.2 CLI commands

```text
Shipped today:
- lettuce init
- lettuce onboard
- lettuce run
- lettuce status
- lettuce logs
- lettuce subscribe
- lettuce add-source <type>
- lettuce add-handler <template>
- lettuce reviews
- lettuce review-approve
- lettuce review-decline

Planned or historical in this build-plan document:
- lettuce run --daemon
- lettuce discover <org>
- pull-subscriptions style shared-stream mirroring
```

### 4.3 Default handlers shipped

- `default-lens.md` — generalist; surfaces anything notable.
- `discovery-lens.md` — looks for product/business opportunities in incoming signal.
- `accounts-lens.md` — watches for customer signal worth recording or acting on.
- `brain-router.md` — decides whether interpreted signal becomes a new brain commit, an update to an existing entry, or is dropped.
- `linear-router.md` — decides whether a brain entry should produce a Linear ticket.
- `inbox-normalizer.md` — takes raw email/transcript events and produces normalized inbox events for downstream handlers.

Each ships with a thoughtful default prompt. Operators are expected to fork and tune.

### 4.4 Signal source integrations

**Direct input through the agent:**
- Operator gives signal to their agent in whatever surface they already use.
- The agent asks for confirmation when needed, then writes the signal to `streams/inbox/direct/` with provenance such as `source: openclaw.telegram`, `source: openclaw.imessage`, `source: cli`, or `source: discord`.
- Lettuce does not provision duplicate chat bots in v0. Surface ownership, auth, and conversation context stay with the agent runtime.

**Email:**
- Operator runs `lettuce add-source email`.
- The agent records source intent and can ingest operator-selected or forwarded email it already has access to.
- Email-shaped events are written to `streams/inbox/email/`.
- Automatic mailbox polling/provisioning is follow-up runtime work, not a shipped public-v0 command path.

**Fathom (call transcripts):**
- Operator runs `lettuce add-source fathom` to record intent.
- The agent can ingest transcript exports or runtime-accessible samples it already has.
- Automatic transcript polling/backfill is follow-up runtime work, not a shipped public-v0 command path.

### 4.5 Outbound integration: Linear

Linear router (`linear-router.md`) reads brain entries and decides on Linear actions:
- Create a new triage issue
- Update an existing issue (referenced by Linear ID in brain entry frontmatter)
- No-op

OAuth scope: read + write issues. Configurable per-team scoping.

### 4.6 Build sequence

Suggested order, optimized for shippability:

1. **Repo + CLI scaffold + `lettuce init`.** The bootstrapper that creates a personal Lettuce repo with default structure. Standalone, no runtime needed.
2. **Default handlers as markdown files.** Just write the prompts. No runtime executing them yet.
3. **Runtime loop — local-only, manual triggers.** Implement the core invocation loop: read events from a stream, find subscribed handlers, invoke LLM, parse output, write publishes. Skip cron, skip remote streams, skip git operations — just file I/O for now.
4. **Git integration.** Add the commit-on-publish behavior. Now publishes are real git commits.
5. **Agent direct-input ingestion.** First end-to-end: operator gives signal to their agent → agent writes a provenance-rich stream event → handler runs → brain entry committed.
6. **Email source.** Second end-to-end. Same protocol flow, harder access/selection problem.
7. **Call transcript source + historical backfill.** Third end-to-end.
8. **Linear router + outbound action.** Now the loop closes — signal in, action out.
9. **Remote stream subscription + policy enforcement.** Multi-repo support.
10. **Onboarding conversation script.** The polished install flow — agent walking the operator through phases 1–5.
11. **Documentation: README, HANDLERS.md, QUICKSTART.md, CONTRIBUTING.md.**
12. **Demo Loom.** 90-second video showing onboarding + first signal flowing through.

Each step should produce something runnable. After step 5, a real operator could plausibly use it. After step 10, it's shippable as v0.

### 4.7 Open implementation decisions

The implementer should make explicit decisions on these and document them as ADRs in the repo:

1. **CLI implementation language.** Recommendation: TypeScript or Python, whichever the implementer is faster in. Both have good GitHub API and LLM SDK support.
2. **Storage of `.lettuce/` runtime state.** Recommendation: gitignored from the brain repo, stored locally in `~/.lettuce/<repo-id>/`. Don't pollute commit history with checkpoint updates.
3. **LLM provider.** Recommendation: Anthropic API (Claude) as default; abstracted behind a provider interface so other models work. The `model` field in handler frontmatter selects.
4. **Email infrastructure.** Recommendation: Postmark Inbound for v0. Cheapest path to a working forwarding address with webhook delivery.
5. **Concurrency.** Recommendation: single-worker for v0. No parallel handler execution. Add a worker pool in v0.2 if performance demands it.
6. **Git operations.** Recommendation: `simple-git` (Node) or `gitpython`, plus the GitHub API for repo creation and permission checks.

### 4.8 Definition of done for v0

v0 is shipped when:

- A new operator can install Lettuce, have their agent walk them through onboarding, and end up with a working Lettuce in under 15 minutes.
- At least one signal source flows into their brain end-to-end.
- The default lenses produce useful brain entries on real signal (judgment call by the implementer; should be visibly better than dumping raw transcripts).
- The Linear router successfully creates a triage ticket from a brain entry on a test invocation.
- The repo is public on GitHub with README, HANDLERS.md, and a working `lettuce init`.
- A landing page is live with a Loom demo.

---

## Part 5: Principles for the Implementer

When this spec is silent, fall back to:

1. **Ship the minimum viable version of any feature.** v0 is not v1. Polish later.
2. **Prefer obvious code over clever code.** This is a protocol meant to be readable by future contributors.
3. **Write the docs as you go.** A handler that isn't documented in HANDLERS.md isn't really shipped.
4. **Favor reversibility.** Anything the runtime does should be undoable by the operator. Git is your friend.
5. **Surface every error to the operator.** No silent failures. Ever.
6. **Don't build IAM.** Inherit permissions from GitHub and OAuth. If you find yourself writing role-mapping logic that isn't a thin wrapper over GitHub teams, stop.
7. **Don't centralize anything on a server.** v0 is operator-owned, no hosted infrastructure. The hosted tier comes later, separately.
8. **When in doubt about scope, do less.** If a feature feels like it might be v0.2, it is.

---

## Part 6: What Comes After v0

For context on where this is going, but **not in scope for v0**:

**v0.2 (next 1–2 months):**
- Adapters for Claude Code and Codex.
- Polished multi-operator coordination (cross-Lettuce subscription, conflict surfacing).
- More signal sources (Slack, GitHub Issues, Notion).
- More routers (Slack, Calendar, Notion).
- Marketplace of community-contributed handlers.

**v1 (next 3–6 months):**
- Self-hostable runtime that doesn't depend on OpenClaw — same protocol, runs as a daemon, agent-agnostic.
- Webhook-driven event delivery instead of polling.
- Derived index for fast querying at scale.

**Hosted tier (next 6–12 months):**
- Managed stream infrastructure with reliability, scale, identity, audit, observability.
- Enterprise features: SSO, on-prem option, compliance certifications.
- Pricing along standard SaaS dimensions (operators, volume, retention).

The implementer of v0 should be aware of this trajectory but not optimize for it. v0 succeeds if it makes one operator's agent meaningfully better at their work.

---

## Appendix A: Glossary

- **Brain** — durable, structured work-context for a given (operator, org) pair. Implemented as a directory of markdown files in a stream.
- **Handler** — markdown file declaring subscriptions, publications, triggers, and an LLM prompt. Unit of work in Lettuce.
- **Lens** — handler convention: subscribes to inbox streams, publishes to brain streams. Interpretive layer.
- **Router** — handler convention: subscribes to brain streams, publishes to outbox streams or service APIs. Action layer.
- **Stream** — git directory of markdown event files. Durable or scoped log.
- **Policy** — declaration in `lettuce.yml` of who can read/write streams. Augments GitHub permissions.
- **Operator** — the human using Lettuce. Their agent runs the runtime on their behalf.
- **Org** — the company or organization a Lettuce install is associated with. One Lettuce per (operator × org) pair.
- **Personal Lettuce repo** — the operator's private git repo containing their handlers, brain, and streams.
- **Shared company Lettuce repo** — a git repo in the company's GitHub org containing cross-team shared streams. Optional.
- **Marker file** — `lettuce.yml` at the root of every Lettuce repo. Used for discovery and configuration.

---

## Appendix B: References

- `HANDLERS.md` — the full handler specification (sibling document).
- `README.md` — the public-facing pitch and protocol overview that ships with the open-source repo.
- `index.html` — the landing page. Useful as a reference for product vocabulary, brand voice, and the staged value-prop progression that should be reinforced in onboarding copy.

---

## Final note to the implementer

The shape of Lettuce is more important than any individual feature. Operator sovereignty, markdown legibility, inheritance over invention, conversation over configuration — these are the things that make Lettuce *Lettuce*, not the specific lenses or routers shipped in v0. When trade-offs come up, prefer the choice that strengthens the shape, even if it costs a feature.

Build the smallest thing that's recognizably Lettuce. Ship it. Then iterate.
