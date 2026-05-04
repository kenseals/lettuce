# Quickstart

This quickstart exercises the current v0 protocol loop locally. It does not provision external Telegram, email, Fathom, Linear, or shared-git integrations.

## Install locally

From the repo root, use a non-editable install for the cleanest fresh-install smoke:

```bash
python3 -m pip install .
lettuce --help
```

For editable development installs, upgrade pip first so PEP 660 editable installs are available:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

If you do not want to install the console script, every command below also works as `python3 -m lettuce.cli ...`.

## Create a personal Lettuce repo

Use the first-pass onboarding helper when the agent already has a direct sample to ingest:

```bash
printf 'Customer says agent context is stale.\n' > /tmp/lettuce-first-signal.md
lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --openclaw-provider \
    --commit
```

`--body "..."` is fine for a one-line smoke test. For real operator messages, use `--body-file` or stdin so pasted formatting survives. Use `--openclaw-provider` for actual OpenClaw dogfood; omit it only when you want an offline deterministic plumbing test.

Or scaffold without ingesting:

```bash
lettuce init ./lettuce-demo --org demo --operator you
lettuce discover ./lettuce-demo
```

This creates a markdown+git repo with `lettuce.yml`, default handlers, inbox streams, brain streams, local checkpoints, and logs.

## Add signal

Import a local file, or repeatedly sample a local export directory:

```bash
printf '# Customer signal\n\nCustomer says agent context is stale.' > /tmp/customer-signal.md
lettuce add-source file ./lettuce-demo --input /tmp/customer-signal.md --commit

mkdir -p /tmp/lettuce-export
printf '# Sales call\n\nCustomer needs fresher agent context.' > /tmp/lettuce-export/sales-call.md
lettuce add-source directory ./lettuce-demo --input /tmp/lettuce-export --sample-limit 3 --commit
```

Directory imports are checkpointed, so the next run only imports new or changed `.md`/`.txt` files.

Or ingest direct operator input that the agent already received:

```bash
lettuce ingest-direct ./lettuce-demo \
  --title "Demo signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --commit
```

For an operator-forwarded email, keep it email-shaped while still using the standard direct-lens stream:

```bash
lettuce ingest-email ./lettuce-demo \
  --subject "Codex Product Update" \
  --body-file /tmp/lettuce-forwarded-email.md \
  --message-id <gmail-message-id> \
  --thread-id <gmail-thread-id> \
  --from "OpenAI <noreply@email.openai.com>" \
  --forwarded-by ken \
  --consent operator-forwarded-email \
  --commit
```

## Configure future sources

These commands record repo-owned source intent. They do not provision external services yet.

```bash
lettuce add-source email ./lettuce-demo \
  --name support-forward \
  --address support@example.com \
  --access-status available_now \
  --sample-policy first-5-operator-approved \
  --privacy-notes "skip personal, legal, medical, and unrelated mail" \
  --commit
lettuce add-source granola ./lettuce-demo \
  --name sales-calls \
  --workspace demo \
  --access-status needs_setup \
  --setup-next-action "connect existing Granola export or MCP before polling" \
  --commit
```

## Add a handler

```bash
lettuce add-handler lens ./lettuce-demo \
  --id pricing-lens \
  --name "Pricing Lens" \
  --publishes brain/pricing \
  --commit
```

## Record a shared stream subscription

This records subscription intent first. For the local proof, `pull-subscriptions` can then import events from another local Lettuce repo into a shared mirror stream with provenance and checkpoints.

```bash
lettuce subscribe ./lettuce-demo \
  --remote /tmp/lettuce-upstream \
  --stream brain/decisions \
  --local-stream streams/shared/decisions \
  --policy 'allow_streams=streams/shared/*' \
  --commit
lettuce pull-subscriptions ./lettuce-demo --commit
```

## Run handlers and update the brain

```bash
lettuce run ./lettuce-demo --commit
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
find ./lettuce-demo/brain -type f | sort
```

By default, handler outputs publish directly to local `brain/*` streams with provenance and git history. Use `--review` only when you want optional calibration or human approval before a brain update lands; then `lettuce reviews`, `review-approve`, and `review-decline` are available.

Without provider configuration, Lettuce uses the bundled deterministic provider adapter so the file, stream, checkpoint, log, brain, and git loop can be tested without model credentials. `lettuce run` prints handler start/finish progress to stderr and keeps machine-readable run JSON on stdout.

To use the OpenClaw model-backed provider seam:

```bash
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
lettuce run ./lettuce-demo --openclaw-provider --commit
```

Use `--handler-command "<command>"` only when testing a custom provider adapter. Use `LETTUCE_HANDLER_TIMEOUT_SECONDS` to cap each handler command invocation. The OpenClaw adapter also honors `LETTUCE_OPENCLAW_TIMEOUT_SECONDS` for the nested model command.

## Verify

```bash
python3 -m unittest discover -s tests
python3 -m lettuce.runtime --smoke
```
