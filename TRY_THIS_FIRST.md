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
printf 'Customer says agent context is stale and wants the agent to remember work context better.\n' > /tmp/lettuce-first-signal.md

lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Demo signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --commit
```

Add `--openclaw-provider` when running inside OpenClaw and you want model-backed handler judgment. Omit it for offline plumbing smoke tests.

## 3. Check state

```bash
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
find ./lettuce-demo/brain -type f | sort
git -C ./lettuce-demo status --short
```

A clean first run should leave a git-backed Lettuce repo with:

- one direct input event under `streams/inbox/direct/`
- one or more durable context entries under `brain/*`, or clear skip reasons in logs
- runtime checkpoints/logs under `.lettuce/`
- clean git status after committed actions

Optional review mode is available for calibration or sensitive changes:

```bash
lettuce run ./lettuce-demo --review --commit
lettuce reviews ./lettuce-demo
```

## 4. Run the synthetic QA fixture

```bash
bash examples/synthetic-corpus/run.sh /tmp/lettuce-synthetic-demo
```

Default behavior uses deterministic fallback and exercises the file, stream, brain, checkpoint, log, and git loop.

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

This runs onboarding, prints status/logs, and confirms the demo repo git status.

## Current baseline

Current public-v0 candidate is merged into `main`.

Latest local verification:

- `python3 -m unittest discover -s tests` -> 74 tests passing
- `python3 -m py_compile lettuce/*.py`
- `python3 -m lettuce.runtime --smoke`
- fresh venv install/use smoke with installed `lettuce` CLI, `onboard`, `status`, logs, and clean demo git state
- OpenClaw-backed onboarding dogfood produced brain updates directly with provenance and git history
