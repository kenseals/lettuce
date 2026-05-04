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

For the operator-style guided setup, use:

```bash
lettuce setup --commit
```

This introduces Lettuce, confirms the operator wants to continue, asks for the org/operator/repo, configures manual/direct ingestion, optionally records email and transcript source intent, ingests a first setup signal, runs handlers behind the review gate, and ends with a summary of how the agent should use Lettuce going forward.

For lower-level scripted setup, use the first-pass onboarding helper when the agent already has a direct sample to ingest:


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
  --review \
  --commit
```

`--body "..."` is fine for a one-line smoke test. For real operator messages, use `--body-file` or stdin so pasted formatting survives. Use `--openclaw-provider` for actual OpenClaw dogfood; omit it only when you want an offline deterministic plumbing test.

Or scaffold without ingesting:

```bash
lettuce init ./lettuce-demo --org demo --operator you
lettuce discover ./lettuce-demo
```

This creates a markdown+git repo with `lettuce.yml`, default handlers, inbox streams, brain streams, local checkpoints, and logs.

To scaffold the optional company hub convention instead:

```bash
lettuce init ./lettuce-demo-hub --org demo --operator you --repo-type company_hub
```

That adds a curated `streams/shared/*` layout plus starter hub docs for shared stream catalog and ownership/policy notes. It is for accepted shared context, not for dumping every operator inbox or transcript.

## Add signal

Import a local file:

```bash
printf '# Customer signal\n\nCustomer says agent context is stale.' > /tmp/customer-signal.md
lettuce add-source file ./lettuce-demo --input /tmp/customer-signal.md --commit
```

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

This records subscription intent only. Shipped today: the subscription record, export-policy checks for local-path remotes, and validation that the local mirror path stays under `streams/shared/*`. Not shipped yet: remote git polling or a `pull-subscriptions` mirror command.

```bash
lettuce subscribe ./lettuce-demo \
  --remote github.com/demo/lettuce-demo \
  --stream streams/shared/decisions \
  --local-stream streams/shared/decisions \
  --commit
```

## Run handlers and review proposals

```bash
lettuce run ./lettuce-demo --review --commit
lettuce reviews ./lettuce-demo
lettuce review-approve ./lettuce-demo <review-id> --operator you --commit
lettuce review-decline ./lettuce-demo <review-id> --reason "not useful" --operator you --commit
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
```

`--review` writes handler outputs to `reviews/pending` instead of publishing directly to `brain/*`. Approving a review publishes it to its target stream and moves the review record to `reviews/approved`; declining moves it to `reviews/declined` without publishing. Omit `--review` only for direct-publish plumbing tests.

Without provider configuration, Lettuce uses the bundled deterministic provider adapter so the file, stream, checkpoint, log, review, and git loop can be tested without model credentials. `lettuce run` prints handler start/finish progress to stderr and keeps machine-readable run JSON on stdout.

To use the OpenClaw model-backed provider seam:

```bash
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
lettuce run ./lettuce-demo --openclaw-provider --review --commit
```

Use `--handler-command "<command>"` only when testing a custom provider adapter. Use `LETTUCE_HANDLER_TIMEOUT_SECONDS` to cap each handler command invocation. The OpenClaw adapter also honors `LETTUCE_OPENCLAW_TIMEOUT_SECONDS` for the nested model command.

## Verify

```bash
python3 -m unittest discover -s tests
python3 -m lettuce.runtime --smoke
```
