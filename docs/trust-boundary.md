# Lettuce Trust Boundary

This document formalizes the trust boundary between the local Lettuce CLI, the agent runtime wrapper that operates it, and future shared-stream or MCP-style multi-repo modes.

Status note: the shared-stream boundary is only partially implemented in public v0. Export declarations, subscription records, local-path export checks, and local mirror-path validation ship now; real pull/mirror execution remains roadmap work tracked alongside issues `#20`, `#35`, `#36`, `#37`, and `#38`.

The short version:

- the runtime owns access to the outside world;
- Lettuce owns durable protocol state inside the repo;
- shared-stream reads and writes must stay scoped to explicit mirror paths and policy boundaries;
- `brain/*` is durable interpreted context and should not be mutated by external systems directly.

## Boundary Summary

The runtime wrapper owns:

- chat, email, browser, OAuth, API keys, MCP connectors, and schedulers;
- deciding whether it currently has permission to fetch outside signal;
- selecting operator-approved signal to ingest;
- executing recurring jobs or remote pulls.

Lettuce owns:

- `lettuce.yml`;
- `streams/*` event storage and provenance;
- `handlers/*`;
- `brain/*`;
- `sources/*`;
- `reviews/*`;
- `subscriptions/*`;
- `.lettuce/*` checkpoints and runtime logs;
- git history for all of the above.

Lettuce should not create duplicate chat, inbox, browser, OAuth, or connector surfaces. The runtime fetches or receives external signal first, then writes selected signal into Lettuce with provenance.

Role-agent repos follow the same boundary. They are first-class Lettuce repos with a bounded GitHub identity behind them, typically recorded as `permission_basis: github-app`, `machine-user`, or `github-user`. They should stay private by default and scoped to that identity's permitted sources and repos; they must not become all-seeing org brains simply because they are automated.

Optional `company_hub` repos follow the same outer GitHub boundary. They narrow behavior further: shared pulls and mirrors may only write under `streams/shared/*`, and the hub should store curated shared context rather than every operator's raw inbox or transcripts.

## Trust Modes

### 1. Local CLI

The CLI runs against one local repo already available on disk. It may mutate local Lettuce state, but only through repo-scoped operations.

What it does not own:

- fetching from remote SaaS APIs;
- managing OAuth or inbox/browser sessions;
- deciding new operator permissions beyond the runtime's current access.

### 2. Runtime Wrapper

The runtime wrapper is the trusted execution layer around Lettuce. It may:

- read external systems the operator has already authorized;
- stage direct/email/file signal for ingestion;
- own the real cadence for manual, after-meeting, daily, source-check, or subscription-pull maintenance loops;
- invoke `lettuce` commands;
- decide whether to run in direct-apply mode or review mode;
- execute future subscription pulls.

The runtime wrapper must still preserve Lettuce's path and provenance rules when it writes into the repo.

### 3. Shared-Stream / Remote / MCP Mode

This is the future multi-repo mode where one Lettuce mirrors selected streams from another Lettuce or shared org repo.

Rules:

- remote signal is imported into explicitly configured local mirror paths, not directly into `brain/*`;
- the safe default mirror surface is `streams/shared/*`;
- remote policies can further narrow what may be mirrored;
- GitHub or runtime access is the outer boundary, but Lettuce path policy is the inner boundary.

## Operation Classes

### Read-only

Examples:

- `status`, `logs`, `reviews`, reading `brain/*`, `sources/*`, `subscriptions/*`;
- reading shared stream files already mirrored locally.

Allowed from:

- local CLI;
- runtime wrapper;
- shared-stream mode.

No durable mutation occurs.

### Stream-write

Examples:

- `add-event`;
- `ingest-direct`;
- `ingest-email`;
- writing normalized handler publishes to `streams/*` or outbox streams.

Allowed from:

- local CLI for local streams;
- runtime wrapper after it has already obtained the external signal.

Rules:

- preserve provenance and consent metadata;
- shared imports must land under `streams/shared/*`, never directly into `brain/*`.

### Source-config-write

Examples:

- `add-source`;
- updating source intent under `sources/*`.

Allowed from:

- local CLI;
- runtime wrapper.

Rules:

- source records describe access and setup intent only;
- they do not imply that Lettuce itself owns OAuth, polling, or connector setup.

### Review-write

Examples:

- `run --review` creating `reviews/pending/*`;
- `review-approve`;
- `review-decline`.

Allowed from:

- local CLI;
- runtime wrapper.

Rules:

- review proposals are repo-owned artifacts;
- approval may publish the reviewed change to its target local stream;
- review is the narrow trust gate before sensitive or operator-requested durable updates.

### Brain-apply

Examples:

- handler publishes directly to `brain/*`;
- `review-approve` promoting a pending review into `brain/*`.

Allowed from:

- local CLI;
- runtime wrapper.

Rules:

- only local Lettuce execution may mutate `brain/*`;
- remote/shared subscriptions must not write into `brain/*` directly;
- review mode is recommended for onboarding, calibration, sensitive updates, and any high-impact flow.

### Subscription-pull

Examples:

- future `pull-subscriptions`;
- runtime-managed mirroring from another Lettuce into a local shared mirror.

Allowed from:

- runtime wrapper;
- a future shared-stream-capable CLI command that still runs locally.

Rules:

- import into configured local mirror paths only;
- local mirror path must remain under `streams/shared/*`;
- remote repos may only declare shareable streams through explicit `lettuce.yml` exports, and those exports must also stay under `streams/shared/*`;
- policy strings such as `allow_streams=...` may only widen inside `streams/shared/*`, not into `brain/*`, `sources/*`, `reviews/*`, or `subscriptions/*`;
- export metadata narrows or documents intent inside the GitHub boundary; it never grants access GitHub itself denies;
- after mirroring, local handlers may read the shared stream and decide whether anything should update `brain/*`.
- external cron/runtime wrappers should keep calling local Lettuce commands; Lettuce still does not own connector credentials or a background scheduler.

### Admin / Destructive

Examples:

- deleting repo content;
- rewriting git history;
- removing source/subscription/review files;
- destructive resets.

Allowed from:

- only by explicit operator/runtime decision;
- never as an automatic side effect of normal ingest or shared pulls.

## Mutation Rules By Path

### `brain/*`

Can be mutated by:

- local handler publishes;
- local review approvals that publish reviewed content;
- local repo edits by the operator or their runtime.

Cannot be mutated by:

- raw external systems;
- shared subscription pulls;
- remote repos writing directly across the boundary.

Trust mode:

- local CLI or runtime wrapper only.

### `sources/*`

Can be mutated by:

- `add-source`;
- explicit local edits to source records.

Meaning:

- durable declaration of source contract, access status, sample policy, privacy notes, and next setup step.

Trust mode:

- local CLI or runtime wrapper only.

### `reviews/*`

Can be mutated by:

- `run --review` creating pending proposals;
- `review-approve`;
- `review-decline`;
- explicit local edits during an operator-approved review-edit flow.

Cannot be mutated by:

- shared subscription pulls;
- direct remote writes.

Trust mode:

- local CLI or runtime wrapper only.

### `subscriptions/*`

Can be mutated by:

- `subscribe`;
- explicit local edits to subscription intent records.

Rules:

- records durable intent and mirror constraints;
- configured local mirror target must stay inside `streams/shared/*`;
- policy declarations for pull boundaries must stay inside `streams/shared/*`.

Trust mode:

- local CLI or runtime wrapper only.

## Shared-Stream Guardrails

The runtime must preserve two levels of protection for shared-stream ingestion:

1. Path boundary: remote/shared content mirrors into `streams/shared/*` only.
2. Policy boundary: subscription policy must not authorize local writes outside `streams/shared/*`.

Current repo enforcement:

- subscription configuration rejects `local_stream` values outside `streams/shared/*`;
- `allow_streams=...` subscription policies are rejected unless they stay within `streams/shared/*`.

This means a subscription record cannot be configured to mirror directly into `brain/*`, `sources/*`, `reviews/*`, or `subscriptions/*`.

## Why This Boundary Exists

The runtime is best positioned to authenticate to external systems and decide what it can see right now.

Lettuce is best positioned to:

- preserve durable org-scoped state;
- keep provenance inspectable;
- keep shared imports separate from interpreted local context;
- make all durable mutations reviewable in git history.

That separation keeps the protocol honest: external access remains runtime-owned, while durable memory and provenance remain repo-owned.
