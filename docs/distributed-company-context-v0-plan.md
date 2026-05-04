# Distributed company context v0 plan

## Position

Lettuce v0 should be **hybrid, personal-first**.

The core unit is a Lettuce repo owned by one operator/agent identity inside one org. That identity may be a human operator's agent or a non-human role agent. Each repo owns private signal, local handlers, local reviews, and local brain state.

Company-wide context should exist as **curated shared streams**, optionally gathered through a company hub repo. The hub must not become a centralized dump of every raw inbox, transcript, Slack thread, and tool event. It should hold approved org-level context: decisions, customer/account summaries, incidents, project updates, and stream discovery metadata.

In short:

```text
operator or role-agent Lettuce repo
  private signal + local brain
  publishes selected shareable stream events

optional company hub Lettuce repo
  discovery index + policies + curated org streams + accepted company truth

other Lettuce repos
  subscribe to explicit exported streams
  later mirror them into streams/shared/*
  run local handlers before updating local brain/*
```

This preserves the differentiated thesis: **distributed company context for agents without centralizing everyone's raw signal.**

## Why not pure centralized

A centralized company brain is easier to explain, but it collapses Lettuce into the same category as every company-RAG/context product. It also breaks the strongest security story: an operator's agent naturally inherits the operator's existing access and context.

If all signal must flow into a central system first, Lettuce becomes another integration platform with a permission problem. That is not the wedge.

## Why not pure distributed

Pure distributed is elegant but too loose for v0. It creates immediate hard problems:

- discovery ambiguity: which repos and streams matter?
- permission laundering: one agent may publish sensitive context too broadly;
- stale/conflicting truth: two agents can publish different interpretations;
- onboarding overhead: solo operators should not need federation concepts on day one;
- non-human role agents could accidentally become overpowered aggregators.

So v0 should ship the distributed primitive, but with an optional hub convention once more than one Lettuce exists in an org.

## Core architecture

### 1. Personal/role Lettuce repo

One repo per `(org, owner identity)`.

Examples:

- `lettuce-acme-ken`
- `lettuce-acme-support-agent`
- `lettuce-acme-sales-assistant`

Naming convention: `lettuce-{org}-{owner-id}` where `owner-id` is the operator handle for human-owned repos and the `role_agent_id` for role-agent repos.

Each repo contains:

- `lettuce.yml`
- `sources/*`
- `streams/inbox/*`
- `streams/shared/*`
- `handlers/*`
- `brain/*`
- `reviews/*`
- `subscriptions/*`

Private by default.

### 2. Company hub repo

Optional, introduced when an org has more than one Lettuce or wants shared company truth.

Example:

- `lettuce-acme-hub`

The hub contains:

- exported shared streams;
- accepted company decisions/facts;
- org-level policies and owners;
- a discovery index of known Lettuce repos/streams;
- maybe default handler packs later.

It should not contain everyone's raw private signal by default.

### 3. Shared streams

A repo may export selected streams. Other repos may record subscriptions to those streams now. Planned next: subscription pulls mirror remote events into local `streams/shared/*` only.

Remote/shared content is **signal**, not truth. It never writes directly into another repo's `brain/*`. The receiving repo's handlers decide whether and how to promote it.

### 4. Non-human role agents

Role agents are first-class Lettuce owners, not special cases inside the hub.

A role agent repo should declare:

- `owner_kind: role_agent`
- `role_agent_id`
- `permission_basis: github-app | machine-user | github-user`
- bounded source credentials and GitHub permissions
- private-by-default repo visibility unless an explicit org policy says otherwise

The rule: a role agent should inherit a bounded identity's access, not magically accumulate all org context.

## Permission model

Lettuce should not build IAM in v0.

Use layered constraints:

1. **Outer boundary:** source credentials and GitHub repo access.
2. **Identity:** GitHub user, machine user, or GitHub App installation.
3. **Repo visibility:** personal/role repos private by default; hub lives in the org.
4. **Policy layer:** `lettuce.yml` narrows what GitHub allows. It never grants access GitHub denies.
5. **Mirror boundary:** remote subscription pulls only write under `streams/shared/*`.
6. **Brain boundary:** only local runtime/review approvals write to local `brain/*`.
7. **Export boundary:** shared exports require explicit exported stream metadata, provenance, and sensitivity.
8. **Review boundary:** shared exports and accepted company decisions default to review in v0 unless explicitly configured otherwise.

## Minimum protocol primitives for v0

### `lettuce.yml` repo identity

Add explicit repo identity fields:

```yaml
lettuce_version: 0.1.0
type: personal # personal | company_hub
org: acme
owner_kind: human_operator # human_operator | role_agent
operator: ken
role_agent_id: null
permission_basis: github-user # github-user | github-app | machine-user
visibility: private
```

### Export schema

Repos should declare what they intentionally share:

```yaml
exports:
  - stream: streams/shared/customers
    description: Curated account/customer updates safe for sales and support agents
    sensitivity: internal
    owner: sales
    allowed_readers: github:team:acme/customer-facing
    allowed_writers: github:team:acme/sales
    review_required: true
```

### Subscription records

`subscriptions/*.md` should track:

- remote repo;
- remote stream;
- local mirror path;
- consent/policy note;
- checkpoint;
- last pulled origin commit/event id.

### Pull/mirror command

Planned next, not shipped in public v0:

Implement `lettuce pull-subscriptions`:

- fetch remote repo or read local path;
- read remote `lettuce.yml`;
- verify the stream is exported;
- copy new events into `streams/shared/<subscription>/`;
- preserve origin metadata;
- checkpoint by origin commit and event id.

### Provenance envelope

Every mirrored event should include:

```yaml
origin_repo: github.com/acme/lettuce-acme-ken
origin_stream: streams/shared/customers
origin_event_id: 2026-05-04T...
origin_commit: abc123
mirrored_at: 2026-05-04T...
subscription_id: acme-ken-customers
source_sensitivity: internal
```

### Company truth metadata

For hub-level accepted truth or decisions:

```yaml
status: active # active | superseded | disputed | draft
decision_owner: sarah
supersedes: previous-event-id
effective_at: 2026-05-04T00:00:00Z
source_events:
  - github.com/acme/lettuce-acme-ken:streams/shared/customers/event.md
confidence: medium
```

## v0 onboarding shape

### Solo founder

Do not introduce heavy federation language.

Flow:

1. Create personal Lettuce repo.
2. Add direct/manual signal.
3. Add one source plan: email, transcripts, or directory import.
4. Run first handler pass.
5. Ask: “Do you want this repo pushed to GitHub as your durable remote?”
6. Mention shared streams as future-ready, not required.

### Org with multiple operators

Flow:

1. Create personal/role Lettuce repo.
2. Scan GitHub org for `lettuce.yml` repos.
3. Surface candidates: personal repos, role-agent repos, hub repo if present.
4. If no hub exists, ask whether to create `lettuce-{org}-hub`.
5. Subscribe only to explicit exported streams.
6. When mirroring ships, mirror into `streams/shared/*`.
7. Run local handlers to decide what enters local brain.

If a hub is created, treat it as curated shared company context only. The initial shared stream convention is:

- `streams/shared/decisions`
- `streams/shared/customers`
- `streams/shared/incidents`
- `streams/shared/projects`

The hub is not the place for every operator's raw inbox, transcript archive, or browser history.

## Failure modes to guard against

### Permission laundering

Sensitive source appears in a shared stream and reaches someone who did not have source access.

Guardrails:

- explicit exports only;
- sensitivity labels;
- shared export review by default;
- provenance preserved;
- no raw inbox/transcript exports by default.

### Hub dump

Company hub becomes noisy RAG.

Guardrails:

- hub accepts curated streams, not raw signal;
- clear stream types;
- decision/status metadata;
- ownership per stream.

### Discovery ambiguity

GitHub scan finds many Lettuce repos but no obvious streams.

Guardrails:

- `exports` schema;
- repo `type` field;
- owner/contact;
- summary descriptions.

### Overpowered role agents

Role agents accumulate broader context than any real role should have.

Guardrails:

- bounded machine user/GitHub App identity;
- explicit source credentials;
- private repo by default;
- review on shared export.

### Conflicting company truth

Two agents publish incompatible summaries/decisions.

Guardrails:

- shared streams remain signal;
- hub accepted truth has owner/status/supersession;
- disputed entries stay visible, not silently overwritten.

## GitHub issue breakdown

1. `#20`, `#35`, `#37`, and `#38` cover the shared-stream, export/policy, and hub roadmap this plan depends on.
2. `#36` is the doc-accuracy pass that keeps public language honest while that roadmap lands.

## Bottom line

The distributed model is still the right bet, but v0 should not pretend every node in the graph can safely federate by magic.

Ship the personal Lettuce as the wedge. Add explicit exports, subscription mirroring, and an optional company hub as the coordination layer. That gives solo founders almost no overhead, while giving 100-person orgs a credible path to shared company context without centralizing everyone's raw signal.
