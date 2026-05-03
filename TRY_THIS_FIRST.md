# Try This First

This is the shortest path to use the current Lettuce v0 protocol loop.

## 1. Install

From GitHub:

```bash
python3 -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

If your shell cannot find the installed `lettuce` script because the user Python bin directory is not on `PATH`, use `python3 -m lettuce.cli ...` for the same commands.

For local development from a cloned repo, upgrade pip first:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

## 2. Create a Lettuce repo from one signal

```bash
printf 'Customer says agent context is stale and wants review before durable updates.\n' > /tmp/lettuce-first-signal.md

lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --review \
  --commit
```

Add `--openclaw-provider` when running inside OpenClaw and you want model-backed handler judgment. Omit it for offline plumbing smoke tests.

## 3. Review proposed updates

```bash
lettuce reviews ./lettuce-demo
lettuce review-approve ./lettuce-demo --first --operator you --commit
# or:
lettuce review-decline ./lettuce-demo <review-id> --reason "not useful" --operator you --commit
```

Approve publishes the reviewed body to its target `brain/*` stream. Decline archives the proposal without publishing.

## 4. Check state

```bash
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
git -C ./lettuce-demo status --short
```

A clean first run should leave a git-backed Lettuce repo with:

- one direct input event under `streams/inbox/direct/`
- one or more review records under `reviews/pending/`, `reviews/approved/`, or `reviews/declined/`
- approved updates under `brain/*`
- runtime checkpoints/logs under `.lettuce/`
- clean git status after committed review actions

## 5. Run the synthetic QA fixture

```bash
bash examples/synthetic-corpus/run.sh /tmp/lettuce-synthetic-demo
```

Default behavior uses deterministic fallback and the public-v0 review gate. Expected smoke shape: synthetic signals ingest, pending reviews are created, direct `brain/*` writes are avoided until approval.

For model-backed judgment inside OpenClaw:

```bash
LETTUCE_SYNTHETIC_PROVIDER=openclaw \
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
bash examples/synthetic-corpus/run.sh /tmp/lettuce-synthetic-demo-model
```

## One-command demo

After installing, run:

```bash
bash examples/quick-demo.sh /tmp/lettuce-demo-public
```

This runs onboarding, lists reviews, approves the first review, prints status/logs, and confirms the demo repo git status.

## Current baseline

Current public-v0 candidate is merged into `main`.

Latest local verification:

- `python3 -m unittest discover -s tests` -> 74 tests passing
- `python3 -m py_compile lettuce/*.py`
- `python3 -m lettuce.runtime --smoke`
- fresh venv install/use smoke with installed `lettuce` CLI, `onboard --review`, `reviews`, `review-approve --commit`, `status`, and clean demo git state
- OpenClaw-backed onboarding dogfood produced pending reviews, then approved review records and brain entries cleanly
