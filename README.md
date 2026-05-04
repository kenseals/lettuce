# Lettuce

Lettuce is an agent-operated, local-first protocol for giving an operator's agent durable company context that is separate from personal memory, owned by the operator, and portable across agent runtimes.

It gives the agent a markdown+git work brain for one organization, a stream model for connecting signal sources, and explicit handlers for interpreting what matters into durable context. Git history, provenance, source boundaries, and optional review mode are the safety mechanisms; the product is company context for agents.

Current status: **first v0 protocol loop**. The installable `lettuce` CLI scaffolds and runs a markdown+git Lettuce repo. The operator's agent is the runtime: OpenClaw in v0, and later any agent that can read files, call tools, and follow the protocol.

The protocol does not own chat surfaces, inboxes, OAuth grants, or service integrations. The agent runtime owns those. Lettuce teaches the agent how to connect the right signal sources, preserve provenance, write stream events, run handlers, maintain brain updates, and prepare for shared-stream coordination across Lettuces in an organization so company context can become distributed instead of centralized.

## Optional Company Hub

An org can also keep an optional `company_hub` Lettuce repo as a lightweight coordination point for curated shared context.

Use the hub for:

- exported shared streams under `streams/shared/*`
- accepted company decisions and durable facts
- discovery metadata for shared streams
- stream owners and policy notes

Do not use the hub for:

- every operator's raw inbox or transcripts
- direct remote writes into `brain/*`
- a centralized all-seeing company dump

Shared pulls and mirrors may only write under `streams/shared/*`. GitHub access remains the outer boundary; Lettuce export and path policy narrows what gets shared inside that boundary.

## Give This To Your Agent

Give your agent this one link:

```text
https://raw.githubusercontent.com/kenseals/lettuce/main/llms.txt
```

That file tells the agent what Lettuce is, what to install, which docs matter, and how to guide you through setting up the first company-context repo without making you copy a separate prompt.

If your agent prefers an install-runbook style prompt, paste this instead:

```text
Retrieve and follow the instructions at:
https://raw.githubusercontent.com/kenseals/lettuce/main/INSTALL_FOR_AGENTS.md
```

The agent should run the setup helpers itself if it has tool access. You answer setup questions and approve sensitive boundaries; you should not have to learn the CLI first.

## Protocol CLI

Start with `TRY_THIS_FIRST.md` for the shortest usable path. For the product frame, see `docs/company-context-for-agents.md`. For a public-safe first-run walkthrough, see `docs/first-run-demo.md`. The v0 protocol source is `LETTUCE_V0_SPEC.md`; handler format is specified in `HANDLERS.md`. For the full local walkthrough, see `QUICKSTART.md`. For agent-operated setup, see `docs/agent-operated-onboarding.md`; for the formal local/runtime/shared trust model, see `docs/trust-boundary.md`; for post-setup verification, see `docs/LETTUCE_VERIFY.md`; for ongoing agent use after setup, see `docs/LETTUCE_RESOLVER.md`; for the OpenClaw source setup contract, see `docs/openclaw-runtime-source-setup.md`; for source setup decisions, see `docs/source-discovery-recipes.md`; for concrete agent-readable setup recipes, see `docs/source-recipes/`; for a repo-packaged OpenClaw skill, see `skills/openclaw-lettuce/SKILL.md`. For the launch note, see `docs/public-v0-launch-note.md`. For the public-v0 release gate, see `docs/public-v0-release-checklist.md`.

Install from GitHub:

```bash
python3 -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

If your shell cannot find the installed `lettuce` script because the user Python bin directory is not on `PATH`, use `python3 -m lettuce.cli ...` for the same commands. For local development from a cloned repo, use `python3 -m pip install .`; for editable installs, upgrade pip first, then run `python3 -m pip install -e .`.

## First Local Loop

```bash
printf 'Customer says agent context is stale.\n' > /tmp/lettuce-first-signal.md
lettuce onboard ./lettuce-demo --org demo --operator you --title "Demo signal" --body-file /tmp/lettuce-first-signal.md --source openclaw.telegram --surface telegram --consent operator-direct-request --openclaw-provider --commit
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
```

That scaffolds an org-scoped Lettuce repo, discovers markdown handlers, writes the first event to `streams/inbox/direct`, writes handler outputs to local `brain/*` streams, records checkpoints/logs under `.lettuce/`, and commits handler/event/brain changes to git when `--commit` is set. Add `--review` when you want calibration or human approval before brain updates land; first agent-operated onboarding should usually use review mode.

`onboard` is the first agent-facing setup helper: it scaffolds the repo if needed, writes the first direct event with provenance, runs handlers, records `onboarding/setup/handoff.json`, and returns a machine-readable status summary. `--openclaw-provider` runs handlers through OpenClaw's model-backed provider for real judgment; omit it only for offline plumbing smoke tests. `--body-file` lets an agent preserve multi-paragraph operator signal without brittle shell quoting; `--body` and stdin remain available for tiny smoke tests.

If the agent already knows the source plan and refresh cadence, record them during onboarding:

```bash
lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --source-plan '{"source_type":"email","name":"customer-mailbox","address":"customers@example.com","access_status":"available_now","sample_policy":"first-3-operator-approved"}' \
  --source-plan '{"source_type":"granola","name":"sales-calls","workspace":"demo-granola","access_status":"needs_setup","setup_next_action":"connect export or MCP before polling"}' \
  --cadence-hint "after-meetings" \
  --cadence-trigger "agent-lane" \
  --handoff-summary "Email is ready now; transcripts need setup before recurring ingest."
```

## Signal Sources

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
lettuce run ./lettuce-demo --openclaw-provider --commit
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

`add-source email|fathom|granola|transcript|zoom` records repo-owned source configuration intent under `sources/` and creates the target stream directory. These records can include `access_status`, `sample_policy`, `privacy_notes`, and `setup_next_action`, so the operator's agent can see whether it can sample now or needs to guide setup first. Manual-only behavior should be described in the recipe/source record body rather than invented as a new CLI status. `lettuce onboard` can create or reuse those same records and then reference them from `onboarding/setup/handoff.json` along with cadence/trigger hints and first-sample outcome. It does not pretend to provision forwarding addresses, OAuth, or webhooks by itself; agent-owned setup can attach to the same source record later.

`subscribe` records remote/shared stream subscription intent under `subscriptions/`. Shipped today: export declarations in `lettuce.yml`, subscription records, local-path export-policy checks, and local mirror-path/policy validation so subscriptions stay scoped to `streams/shared/*`. Not shipped yet: a real `pull-subscriptions` mirror command, remote polling, or checkpointed git mirroring. See `docs/trust-boundary.md` for the formal mutation rules around `brain/*`, `sources/*`, `reviews/*`, and shared-stream mirrors, and see roadmap issues `#20`, `#35`, `#36`, `#37`, and `#38` for the shared-stream/hub buildout.

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

## Minimal Maintenance Loop

Lettuce v0 does not run its own daemon or own chat/email/OAuth/cron surfaces. The external runtime or cron decides when to check, then calls existing commands such as `lettuce status`, `lettuce ingest-*`, `lettuce run --review`, and `lettuce reviews`. Shared-stream mirroring remains planned follow-up work rather than a shipped CLI command.

`lettuce status` now includes repo identity metadata alongside a small `freshness` summary so the agent can tell whether a repo is owned by a `human_operator` or a `role_agent`, whether it is `fresh`, `pending_review`, `blocked_on_setup`, or `idle_manual_only`, and which maintenance modes are configured: `manual`, `after-meeting`, `daily`, `source-check`, and `subscription-pull`. That last mode currently expresses subscription maintenance intent; it does not mean a built-in pull command already exists.

Role-agent repos are first-class Lettuce repos, not hidden company-hub special cases. Use names such as `lettuce-acme-support-agent`, keep them `private` by default, and set `permission_basis` to the bounded GitHub identity that owns the repo access: `github-app`, `machine-user`, or `github-user`. A role agent should inherit only that identity's permitted scope, not become an all-seeing org brain.

## Handler Execution

Handler execution is pluggable through `LETTUCE_HANDLER_COMMAND`. If it is unset, the local protocol loop invokes the bundled default provider adapter with the same stdin/stdout JSON contract, so file, stream, checkpoint, review, and git behavior can be tested without blocking on provider credentials.

To run handlers through the local OpenClaw model stack:

```bash
LETTUCE_HANDLER_COMMAND="python3 -m lettuce.openclaw_provider" \
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
lettuce run ./lettuce-demo --commit
```

The OpenClaw provider is intentionally a thin optional command adapter. It reads the standard handler invocation JSON from stdin, calls `openclaw capability model run --gateway`, extracts the model's JSON handler output, and writes that JSON to stdout for the runtime to validate and publish. During `lettuce run`, handler start/finish progress is printed to stderr while the machine-readable run result stays on stdout; each handler command is capped by `LETTUCE_HANDLER_TIMEOUT_SECONDS`, and the OpenClaw adapter also honors `LETTUCE_OPENCLAW_TIMEOUT_SECONDS` for its nested model call.

## What Lettuce Is Not

- not a generic notes app
- not a vector memory store
- not a company brain by itself
- not a dashboard-first product
- not a first-party chat adapter, inbox provider, or OAuth broker

The core idea is **lenses before routers**: decide what matters and where it should go before downstream agents act.

## Tests

```bash
python3 -m unittest discover -s tests
python3 -m py_compile lettuce/*.py
python3 -m lettuce.runtime --smoke
```

## Historical Docs
