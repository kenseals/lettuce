# Lettuce public v0 launch note

Lettuce v0 is an agent-operated markdown + git protocol for turning messy work signals into reviewed updates to durable operating context.

## What works now

- Installable Python package with `lettuce` console script.
- `lettuce onboard` creates a local Lettuce repo from a first signal.
- Markdown handlers run over stream events.
- `--review` writes proposed updates to `reviews/pending` instead of mutating `brain/*` directly.
- `lettuce reviews`, `review-approve`, and `review-decline` provide the first review/apply loop.
- Source intent records exist for email, transcripts, Telegram, Fathom, Granola, Zoom, and local files without pretending Lettuce owns those external auth surfaces.
- OpenClaw can act as the operator runtime and run model-backed handlers through the optional OpenClaw provider adapter.
- Synthetic corpus smoke tests exercise the review gate without direct brain writes.

## How to try it

```bash
git clone https://github.com/kenseals/lettuce.git
cd lettuce
python3 -m pip install .
lettuce --help
bash examples/quick-demo.sh /tmp/lettuce-demo-public
```

For the shorter manual path, start with `TRY_THIS_FIRST.md`. For the full walkthrough, use `QUICKSTART.md`.

## What is intentionally deferred

- Hosted SaaS runtime.
- First-party Telegram/iMessage/Discord adapters.
- Gmail, Zoom, Fathom, Granola, Linear, or Notion OAuth provisioning.
- Remote shared-git polling and policy enforcement.
- Automatic side effects into work systems.
- Auto-approval policies.
- Polished UI.

The v0 bet is deliberately narrow: prove the protocol shape first. The operator's agent owns conversation, tool access, and external services; Lettuce owns the durable repo shape for streams, handlers, reviews, brain state, logs, and checkpoints.

## Known rough edges

- Model-backed handler runs are useful but slow because handlers currently run serially.
- The default deterministic provider proves plumbing, not judgment quality.
- Review IDs are machine-generated and not yet especially friendly.
- Source connectors are protocol records/importers first, not full integrations.

## Release posture

Ship this as a public v0 protocol repo for curious agent operators and builders. Do not oversell it as a complete app or managed service yet.
