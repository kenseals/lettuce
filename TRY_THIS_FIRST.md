# Try This First

This is the shortest path to test the current Lettuce v0 install/onboarding loop. Run this before testing ongoing usage.

## 0. What this proves

This flow should prove five things:

1. Lettuce installs.
2. `onboard` creates a repo from one signal.
3. `--review` creates pending review proposals instead of writing straight to `brain/*`.
4. `review-approve` publishes one approved update into `brain/*`.
5. committed actions leave a clean git-backed demo repo.

If any step fails, stop there and fix that before testing source discovery or ongoing usage.

## Interactive onboarding happy path

For the conversational operator-style setup, use:

```bash
lettuce setup --commit
```

This introduces Lettuce, asks whether to continue, asks for org/operator/repo/source details, configures manual/direct ingestion, optionally records email and transcript source intent, ingests a first setup signal, runs handlers behind the review gate, and ends with a plain-English summary.

Use this when testing whether onboarding feels right for a real operator. Use the raw `lettuce onboard ...` command below when testing lower-level CLI plumbing.

## 1. Install

From the Lettuce repo root:

```bash
python3 -m pip install .
lettuce --help
```

If your shell cannot find the installed `lettuce` script because the user Python bin directory is not on `PATH`, use `python3 -m lettuce.cli ...` for the same commands.

For editable development installs, upgrade pip first:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

## 2. Create a fresh demo repo from one signal

Use a new throwaway path so old state cannot hide setup bugs:

```bash
rm -rf /tmp/lettuce-demo
printf 'Customer says agent context is stale and wants review before durable updates.\n' > /tmp/lettuce-first-signal.md

lettuce onboard /tmp/lettuce-demo \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source cli \
  --surface cli \
  --consent operator-direct-request \
  --review \
  --commit
```

Expected shape:

- JSON prints to stdout.
- No Python traceback.
- `/tmp/lettuce-demo` exists and is a git repo.
- `reviews/pending/` contains at least one review proposal.

Add `--openclaw-provider` only when running inside OpenClaw and you specifically want model-backed handler judgment. Omit it for fresh install/onboarding smoke tests; the deterministic fallback is better for isolating packaging and CLI issues.

## 3. Review proposed updates

```bash
lettuce reviews /tmp/lettuce-demo
```

Copy one pending review id, then approve it:

```bash
lettuce review-approve /tmp/lettuce-demo <review-id> --operator you --commit
```

Or decline it instead:

```bash
lettuce review-decline /tmp/lettuce-demo <review-id> --reason "not useful" --operator you --commit
```

Approve publishes the reviewed body to its target `brain/*` stream. Decline archives the proposal without publishing.

## 4. Check state

```bash
lettuce status /tmp/lettuce-demo
lettuce logs /tmp/lettuce-demo --limit 5
git -C /tmp/lettuce-demo status --short
find /tmp/lettuce-demo -maxdepth 3 -type f | sort
```

A clean first run should leave a git-backed Lettuce repo with:

- one direct input event under `streams/inbox/direct/`
- one or more review records under `reviews/pending/`, `reviews/approved/`, or `reviews/declined/`
- approved updates under `brain/*` if a review was approved
- runtime checkpoints/logs under `.lettuce/`
- clean git status after committed review actions

## 5. Failure triage

- `lettuce: command not found`: use `python3 -m lettuce.cli ...` or add the user Python bin directory to `PATH`.
- no pending reviews: confirm `--review` was included and `--no-run` was not included.
- direct `brain/*` writes before approval: that is a bug in the review gate path.
- dirty git state after `--commit`: capture `git -C /tmp/lettuce-demo status --short` and fix before testing ongoing usage.
- provider/model errors: rerun without `--openclaw-provider` to separate install/onboarding issues from model-provider issues.

## 6. Run the synthetic QA fixture

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

Merged into `main` at `3d836d3 feat: add Lettuce markdown protocol CLI loop (#3)`.

Verified after merge:

- `python3 -m unittest discover -s tests` -> 65 tests passing
- `python3 -m py_compile lettuce/*.py`
- `python3 -m lettuce.runtime --smoke`
- fresh venv install/use smoke with installed `lettuce` CLI, `onboard --review`, `reviews`, `review-approve`, `status`, and clean demo git state
