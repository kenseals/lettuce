# First Run Demo

This is the short public-safe walkthrough for Lettuce v0: install from GitHub, onboard one signal, write a first durable brain update, and inspect the resulting markdown/git state.

## 1. Install

```bash
python3 -m venv /tmp/lettuce-demo-venv
. /tmp/lettuce-demo-venv/bin/activate
python -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

## 2. Onboard from one messy signal

```bash
cat > /tmp/lettuce-first-signal.md <<'EOF'
A founder says their agent keeps using stale pricing and old onboarding notes.
They want the agent to maintain durable work context with source provenance
so future work starts from the current truth.
EOF

lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Stale agent context" \
  --body-file /tmp/lettuce-first-signal.md \
  --source cli \
  --surface terminal \
  --consent operator-direct-request \
  --commit
```

Expected shape:

```text
lettuce: running accounts-lens on ...
lettuce: accounts-lens ok in 0.1s
lettuce: running default-lens on ...
lettuce: default-lens ok in 0.1s
lettuce: running discovery-lens on ...
lettuce: discovery-lens ok in 0.1s
```

The command initializes a markdown+git Lettuce repo, writes the signal to `streams/inbox/direct/`, runs handlers, writes useful handler output to `brain/*`, records checkpoints/logs, and commits the result when `--commit` is set.

## 3. Inspect durable state

```bash
find ./lettuce-demo/brain -type f -name '*.md' | sort
lettuce status ./lettuce-demo
lettuce logs ./lettuce-demo --limit 5
git -C ./lettuce-demo log --oneline --max-count 5
git -C ./lettuce-demo status --short
```

Expected outcome:

- useful handler output becomes markdown under `brain/*`, or logs explain why it was skipped;
- the original signal remains under `streams/inbox/direct/` with provenance;
- checkpoints/logs show what was processed;
- each committed action is visible in git history;
- `git status --short` is clean after committed actions.

## Optional: calibration review mode

Use review mode only when you want to inspect proposed updates before they land:

```bash
lettuce run ./lettuce-demo --review --commit
lettuce reviews ./lettuce-demo
lettuce review-approve ./lettuce-demo --first --operator you --commit
```

## Optional: one-command local demo

From a cloned Lettuce repo:

```bash
bash examples/quick-demo.sh /tmp/lettuce-demo
```

That script runs the same basic loop with the deterministic local provider so install, onboarding, brain updates, status, logs, and git cleanliness can be checked quickly.

## Optional: Subprocess-backed handler judgment

The normal OpenClaw path is agent-operated judgment. Use `--openclaw-provider` only when deliberately testing the older subprocess adapter:

```bash
lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Stale agent context" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --commit
```

In the public-v0 gate, the agent-operated path should create useful brain updates for stale-context customer pain and skip irrelevant noise.
