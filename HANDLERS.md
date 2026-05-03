# Handlers — Lettuce Protocol Specification v0

> Handlers are the unit of work in Lettuce. A handler is a markdown file that declares what it subscribes to, what it does, and where it publishes. Lenses and routers are conventional names for two common types of handlers; the underlying primitive is the same.

This document specifies the handler format for v0. It's intentionally minimal — only what's needed to ship and run handlers reliably. Extensions can be added in later versions without breaking v0 handlers.

---

## Anatomy of a handler

A handler is a single markdown file with YAML frontmatter and a body. The frontmatter declares behavior and metadata; the body contains the prompt the runtime passes to the LLM.

```markdown
---
id: discovery-lens
name: Discovery Lens
type: lens
version: 0.1.0
subscribes:
  - stream: inbox/email
  - stream: inbox/transcripts
publishes:
  - stream: brain/discovery
    mode: append
triggers:
  - on: new-event
batch: false
timeout: 60s
---

# Discovery Lens

You are a continuous-discovery researcher embedded in the company's signal stream.
For each incoming signal, look for:

- Unmet customer needs that could shape product direction
- Friction points customers describe in their own words
- Adjacent problems we're not currently solving
- Competitive moves or market shifts mentioned in passing

For anything you find, produce a brain entry with:
- A short title
- The signal that triggered it (quoted, with attribution)
- Your interpretation
- A suggested next action, if obvious

If you find nothing of note in this signal, return `{"skip": true}` and nothing else.

Output format: ...
```

That's the full structure. Frontmatter on top, prompt on the bottom, both are human-readable, both are editable in any markdown editor.

---

## Frontmatter fields

### Required

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique slug within the Lettuce repo. Used in logs, references, policies. |
| `name` | string | Human-readable name. |
| `type` | string | One of `lens`, `router`, `handler`. See "Types" below — purely conventional, no behavioral difference. |
| `version` | semver | Version of this handler. Bump on edits that change behavior. |
| `subscribes` | array | One or more streams this handler reads from. |
| `publishes` | array | One or more streams this handler writes to. May be empty for handlers that only call services. |

### Optional

| Field | Type | Default | Description |
|---|---|---|---|
| `triggers` | array | `[{on: new-event}]` | What invokes the handler. See "Triggers" below. |
| `batch` | bool | `false` | If true, runtime delivers batches of events instead of one at a time. |
| `batch_size` | int | `10` | Max events per batch when `batch: true`. |
| `timeout` | duration | `60s` | Max wall-clock time per invocation. |
| `model` | string | runtime default | Optional override for which LLM to use (`claude-sonnet-4`, etc.). |
| `description` | string | none | Free-text. Used in agent-facing introspection. |
| `tags` | array | `[]` | Free-text labels. Used by policies to grant or deny capabilities. |
| `depends_on` | array | `[]` | Other handler IDs that must run before this one on the same event. |

### Stream subscription / publication entries

Each entry in `subscribes` and `publishes` is an object:

```yaml
subscribes:
  - stream: inbox/email           # required — relative path within the repo, or remote URI
    filter: "from:customer.com"   # optional — string match or simple expression
    since: "v0-onboarding"        # optional — ref or timestamp; default is "all new events after install"

publishes:
  - stream: brain/discovery
    mode: append                  # append | replace | upsert
    key: "{title}"                # for upsert mode, the dedup key
```

Streams are referenced by path. Local streams (within the same Lettuce repo) use bare paths like `brain/discovery`. Remote streams (in a shared company repo or another operator's published-to-org repo) use the form `<org>/<repo>:<path>`, for example `acme/lettuce-brain:brain/decisions`.

---

## Types

`type` is conventional, not enforced. The runtime treats all types identically — they all subscribe, run, and publish. The convention:

- **`lens`** — interprets incoming signal. Subscribes to inbox streams; publishes to brain streams. The "what does this mean" layer.
- **`router`** — takes interpreted brain content and produces side effects in services. Subscribes to brain streams; publishes to outbox streams or calls APIs directly. The "what should we do about it" layer.
- **`handler`** — anything that doesn't fit the above two patterns cleanly. Pipelines, fact-checkers, summarizers, fan-outs, etc.

Operators and contributors may invent additional conventional types over time. The runtime doesn't care; the type field is for human and agent legibility.

---

## Triggers

Triggers declare what causes the runtime to invoke a handler. v0 supports three:

```yaml
triggers:
  - on: new-event           # fires when any subscribed stream gets a new event
  - on: schedule
    cron: "0 */6 * * *"     # standard cron — every 6 hours
  - on: manual              # only runs when explicitly invoked by another handler or operator
```

A handler may declare multiple triggers (e.g., new-event AND schedule for safety/recovery). v0 runtime fires each trigger independently; deduplication is the handler's responsibility if it matters.

---

## Inputs and outputs

When the runtime invokes a handler, it passes a structured input and expects a structured output.

### Input passed to the handler

The runtime constructs a system prompt + user message containing:

1. The handler body (the prompt) as the system prompt
2. A user message containing one or more events from subscribed streams, in JSON form:

```json
{
  "events": [
    {
      "stream": "inbox/email",
      "id": "2026-04-30T14:22:11Z-abc123",
      "timestamp": "2026-04-30T14:22:11Z",
      "frontmatter": {
        "from": "anna@bigcorp.com",
        "subject": "Quick question about pricing",
        "thread_id": "..."
      },
      "body": "Hi team, wanted to check if your enterprise tier..."
    }
  ],
  "context": {
    "operator": "ken",
    "org": "acme",
    "handler_id": "discovery-lens",
    "invoked_at": "2026-04-30T14:23:00Z"
  }
}
```

### Output expected from the handler

Handlers return a JSON object with one or more publish actions:

```json
{
  "publishes": [
    {
      "stream": "brain/discovery",
      "frontmatter": {
        "title": "Pricing transparency request from BigCorp",
        "source_event": "2026-04-30T14:22:11Z-abc123",
        "tags": ["pricing", "enterprise"]
      },
      "body": "Anna at BigCorp asked about enterprise pricing..."
    }
  ],
  "skip": false
}
```

Or, if the handler decides nothing is worth publishing:

```json
{ "skip": true }
```

Handlers may also return `"errors"` and `"notes"` for runtime logging, but those are optional.

---

## Stream events on disk

Each event published by a handler becomes a markdown file in the destination stream's directory:

```
brain/discovery/
  2026-04-30T14-23-15Z-pricing-transparency-bigcorp.md
```

Filename format: `<ISO-timestamp>-<slugified-title>.md`. Timestamps use hyphens instead of colons for filesystem compatibility.

The file content:

```markdown
---
id: 2026-04-30T14-23-15Z-pricing-transparency-bigcorp
timestamp: 2026-04-30T14:23:15Z
handler: discovery-lens
handler_version: 0.1.0
source_event: 2026-04-30T14:22:11Z-abc123
title: Pricing transparency request from BigCorp
tags: [pricing, enterprise]
---

Anna at BigCorp asked about enterprise pricing...
```

The runtime is responsible for translating the handler's JSON output into properly-formatted markdown files and committing them to the appropriate stream directory.

---

## Lifecycle

For each event arriving in a subscribed stream, the runtime:

1. **Resolves subscribers.** Find all handlers whose `subscribes` matches the stream and filters.
2. **Checks dependencies.** If `depends_on` is set, wait for those handlers to complete on the same source event.
3. **Constructs invocation.** Build the system prompt (handler body) + user message (events as JSON).
4. **Invokes the LLM.** Using the configured model and timeout.
5. **Parses output.** Validate JSON shape; if malformed, log error and skip publishes.
6. **Applies publishes.** Write each publish entry as a markdown file in the destination stream and commit to git.
7. **Records the run.** Append a runtime log entry (handler ID, source event, success/failure, duration, output size).

If any step fails, the runtime logs the failure and continues to the next event. Failures are visible to the operator via runtime logs and never silently swallowed.

---

## Idempotency and replay

Handlers should be designed to be **idempotent on a given source event**: invoking the same handler on the same input event twice should produce the same result, or a no-op the second time.

The runtime supports this by:

- Recording, for each handler, the most recent source event it processed per stream (a "checkpoint").
- On replay, only reprocessing events newer than the checkpoint.
- Allowing operators to manually reset checkpoints if a handler was buggy and needs to reprocess history.

For `mode: upsert` publishes, the runtime checks whether an event with the same `key` already exists in the destination stream and replaces it rather than appending. This prevents duplicate brain entries when the same source event is reprocessed.

---

## Policy interaction

Handlers run in the operator's Lettuce repo. They can publish to:

- **Local streams** (within the same repo): always permitted.
- **Remote streams** (in shared company repos): permitted iff the shared repo's `lettuce.yml` policy grants this operator's role write access to that stream path.

The runtime enforces this at publish time. A handler that tries to publish to a stream it lacks permission for produces a runtime error and the publish is dropped (with a log entry).

This means handlers can be written without knowing whether they'll have access to a given remote stream — the runtime handles the gating. An operator can copy a handler from another operator's repo, and it'll work for the streams they have access to and skip the ones they don't.

---

## Versioning

Handler versions follow semver:

- **Patch** — bug fixes, prompt clarifications that don't change output shape.
- **Minor** — new optional frontmatter fields, new output fields, backwards-compatible behavior changes.
- **Major** — breaking changes to inputs, outputs, or stream paths.

The runtime records the handler version on every published event (in event frontmatter). This means brain entries are traceable to the exact handler version that produced them, which matters when debugging "why did the brain say this thing two months ago" questions.

When `lettuce run --review` or `lettuce onboard --review` is used, handler publishes are written first as review proposals under `reviews/pending/`. The proposal preserves the target stream, source event, handler id, handler version, title, and body. `lettuce review-approve` publishes the reviewed body to its target stream and moves the review record to `reviews/approved/`; `lettuce review-decline` moves it to `reviews/declined/` without publishing.

---

## Default handlers shipped with v0

v0 ships with a default set of handlers operators get out of the box. They live in `handlers/` in the brain template:

**Lenses:**
- `default-lens.md` — generalist; surfaces anything notable.
- `discovery-lens.md` — looks for product/business opportunities.
- `accounts-lens.md` — watches for customer signal.

**Routers:**
- `brain-router.md` — decides whether interpreted signal becomes a brain commit, an update to existing brain content, or is dropped.
- `linear-router.md` — decides whether a brain entry should produce a Linear ticket (create, update, or no-op).

**Helpers:**
- `inbox-normalizer.md` — takes raw email/transcript events and produces a normalized inbox event other lenses can consume cleanly.

These are starting points. Operators are expected to fork, edit, and add their own.

---

## What's deliberately not in v0

To keep the spec minimal and shippable:

- **No streaming output.** Handlers return their full output once. Streaming responses come later.
- **No multi-LLM orchestration within a handler.** A handler invokes one LLM call. Multi-step reasoning happens by chaining handlers via streams.
- **No conditional subscription.** A handler's `subscribes` is static. If you need conditional routing, write a thin upstream handler that filters and republishes.
- **No retry logic in handlers themselves.** The runtime owns retries (and they're conservative — one retry on transient errors, then mark failed).
- **No handler-to-handler direct calls.** All communication is via streams. This is a deliberate constraint to keep the architecture clean.

These can be added in v0.2+ without breaking v0 handlers.

---

## Open questions for v0 build

These are decisions the implementer should make explicitly during v0 build, ideally documented in an ADR (architecture decision record) inside the repo:

1. **Output schema validation.** Should the runtime use JSON schema validation on handler output, or trust handlers to produce well-formed JSON and fail gracefully? Recommendation: lightweight schema validation on the top-level shape (`publishes`, `skip`), trust handler-supplied frontmatter and bodies.

2. **Concurrency.** Can multiple handlers run in parallel on the same source event? Recommendation: yes, but with a simple worker pool; serialize publishes to the same stream to avoid git conflicts.

3. **Git commit grouping.** Should each handler's publishes be a separate commit, or should related handlers' publishes on the same source event be grouped? Recommendation: one commit per handler invocation, with a structured commit message (`<handler-id>: <event-id>`) for greppability.

4. **Stream filename collisions.** What if two handlers publish events with the same timestamp? Recommendation: append a short hash of the source event ID to the filename to disambiguate.

5. **Handler discovery.** How does the runtime find handlers in the repo? Recommendation: scan `handlers/` recursively for `.md` files with frontmatter that includes `type` and `subscribes`. No registry needed.

---

## Summary

A handler is a markdown file with frontmatter declaring subscriptions, publications, and triggers, and a body containing the LLM prompt. The runtime invokes handlers when subscribed streams get new events, passes the events as structured JSON, parses the handler's JSON output, and writes publishes to destination streams as markdown files committed to git. Lenses and routers are conventional names for two common handler patterns; the underlying primitive is the same.

That's the whole spec for v0. Anything else can be added later.
