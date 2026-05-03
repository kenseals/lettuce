# Lettuce

Lettuce is an agent-operated, local-first protocol for giving an operator's agent durable company context that is separate from personal memory, owned by the operator, and portable across agent runtimes.

It gives the agent a markdown+git work brain for one organization, a stream model for connecting signal sources, explicit handlers for interpreting what matters, and a review gate before durable context changes. The review loop is the safety mechanism; the product is company context for agents.

Current status: **first v0 protocol loop**. The installable `lettuce` CLI scaffolds and runs a markdown+git Lettuce repo. The operator's agent is the runtime: OpenClaw in v0, and later any agent that can read files, call tools, and follow the protocol.

The protocol does not own chat surfaces, inboxes, OAuth grants, or service integrations. The agent runtime owns those. Lettuce teaches the agent how to connect the right signal sources, preserve provenance, write stream events, run handlers, review proposed brain updates, and eventually subscribe to other Lettuces in an organization so company context can become distributed instead of centralized.

## Protocol CLI

Start with `TRY_THIS_FIRST.md` for the shortest usable path. For the product frame, see `docs/company-context-for-agents.md`. For a public-safe install-to-approval walkthrough, see `docs/first-run-demo.md`. The v0 protocol source is `LETTUCE_V0_SPEC.md`; handler format is specified in `HANDLERS.md`. For the full local walkthrough, see `QUICKSTART.md`. For agent-operated setup, see `docs/agent-operated-onboarding.md`; for the OpenClaw source setup contract, see `docs/openclaw-runtime-source-setup.md`; for source setup decisions, see `docs/source-discovery-recipes.md`; for a repo-packaged OpenClaw skill, see `skills/openclaw-lettuce/SKILL.md`. For the launch note, see `docs/public-v0-launch-note.md`. For the public-v0 release gate, see `docs/public-v0-release-checklist.md`.

Install from GitHub:

```bash
python3 -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

If your shell cannot find the installed `lettuce` script because the user Python bin directory is not on `PATH`, use `python3 -m lettuce.cli ...` for the same commands. For local development from a cloned repo, use `python3 -m pip install .`; for editable installs, upgrade pip first, then run `python3 -m pip install -e .`.

## First Local Loop

```bash
printf 'Customer says agent context is stale.\n' > /tmp/lettuce-first-signal.md
lettuce onboard ./lettuce-demo --org demo --operator you --title "Demo signal" --body-file /tmp/lettuce-first-signal.md --source openclaw.telegram --surface telegram --consent operator-direct-request --openclaw-provider --review --commit
lettuce reviews ./lettuce-demo
lettuce review-approve ./lettuce-demo --first --operator you --commit
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
```

That scaffolds a personal Lettuce repo, discovers markdown handlers, writes the first event to `streams/inbox/direct`, writes handler outputs to `reviews/pending`, records checkpoints/logs under `.lettuce/`, and commits handler/event/review changes to git when `--commit` is set. `review-approve` publishes an approved proposal to its target `brain/*` stream; `review-decline` moves it to `reviews/declined` without publishing.

`onboard` is the first agent-facing setup helper: it scaffolds the repo if needed, writes the first direct event with provenance, runs handlers, and returns a machine-readable status summary. `--openclaw-provider` runs handlers through OpenClaw's model-backed provider for real judgment; omit it only for offline plumbing smoke tests. `--body-file` lets an agent preserve multi-paragraph operator signal without brittle shell quoting; `--body` and stdin remain available for tiny smoke tests.

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
lettuce run ./lettuce-demo --openclaw-provider --review --commit
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

The first source connector is deliberately local and boring: `add-source file` imports a local text/markdown file into a stream event with source provenance, and `add-source stdin` does the same for piped or supplied text.

`add-source email|fathom|granola|transcript|zoom` records repo-owned source configuration intent under `sources/` and creates the target stream directory. These records can include `access_status`, `sample_policy`, `privacy_notes`, and `setup_next_action`, so the operator's agent can see whether it can sample now or needs to guide setup first. It does not pretend to provision forwarding addresses, OAuth, or webhooks by itself; agent-owned setup can attach to the same source record later.

`subscribe` records remote/shared stream subscription intent under `subscriptions/`. It keeps the markdown protocol shape visible without pretending remote git polling or policy enforcement is implemented yet.

## Handler Execution

Handler execution is pluggable through `LETTUCE_HANDLER_COMMAND`. If it is unset, the local protocol loop invokes the bundled default provider adapter with the same stdin/stdout JSON contract, so file, stream, checkpoint, review, and git behavior can be tested without blocking on provider credentials.

To run handlers through the local OpenClaw model stack:

```bash
LETTUCE_HANDLER_COMMAND="python3 -m lettuce.openclaw_provider" \
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
lettuce run ./lettuce-demo --review --commit
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
