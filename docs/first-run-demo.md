# First Run Demo

This is the short public-safe walkthrough for Lettuce v0: install from GitHub, onboard one signal, review proposals, approve one update, and inspect the resulting markdown/git state.

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
They want a review step before the company brain changes, because one bad
automatic update already confused a sales call.
EOF

lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Stale agent context" \
  --body-file /tmp/lettuce-first-signal.md \
  --source cli \
  --surface terminal \
  --consent operator-direct-request \
  --review \
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

The command initializes a markdown+git Lettuce repo, writes the signal to `streams/inbox/direct/`, runs handlers, and writes review-gated proposals to `reviews/pending/`.

## 3. Review proposals

```bash
lettuce reviews ./lettuce-demo
```

Expected shape:

```json
{
  "reviews": [
    {
      "id": "...-default-lens-...",
      "status": "pending",
      "target_stream": "brain/general",
      "title": "Default Lens: Stale agent context"
    },
    {
      "id": "...-discovery-lens-...",
      "status": "pending",
      "target_stream": "brain/discovery",
      "title": "Discovery Lens: Stale agent context"
    }
  ]
}
```

## 4. Approve one update

Approve the first pending review:

```bash
lettuce review-approve ./lettuce-demo --first --operator you --commit
```

For a specific proposal, copy one review `id` from `lettuce reviews` and pass it instead of `--first`.

Expected shape:

```json
{
  "status": "published",
  "target_stream": "brain/general",
  "publish_path": ".../brain/general/...md"
}
```

## 5. Inspect durable state

```bash
find ./lettuce-demo/brain -type f -name '*.md'
git -C ./lettuce-demo log --oneline --max-count 5
git -C ./lettuce-demo status --short
```

Expected outcome:

- approved proposals become markdown under `brain/*`;
- review files move from `reviews/pending/` to `reviews/approved/`;
- each committed action is visible in git history;
- `git status --short` is clean after committed actions.

## Optional: one-command local demo

From a cloned Lettuce repo:

```bash
bash examples/quick-demo.sh /tmp/lettuce-demo
```

That script runs the same basic loop with the deterministic local provider so install, onboarding, review, approval, status, logs, and git cleanliness can be checked quickly.

## Optional: OpenClaw-backed handler judgment

When running inside OpenClaw, add `--openclaw-provider` to `onboard` or `run`:

```bash
lettuce onboard ./lettuce-demo \
  --org demo \
  --operator you \
  --title "Stale agent context" \
  --body-file /tmp/lettuce-first-signal.md \
  --source openclaw.telegram \
  --surface telegram \
  --consent operator-direct-request \
  --openclaw-provider \
  --review \
  --commit
```

In the public-v0 gate, the OpenClaw-backed path correctly created review proposals for stale-context customer pain and skipped an irrelevant grocery note.
