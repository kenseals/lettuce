# Synthetic Signal Corpus

This corpus is a public-safe Lettuce dogfood lane for testing signal variety before a real company has customer data.

The fake org is **Northstar Tools**, a small team building agent workflow software for support and product teams. All names, emails, customers, and situations are synthetic.

## Why this exists

Use this after Lettuce-for-Lettuce dogfood and before replaying private historical data. It gives repeatable coverage for:

- customer complaints
- sales leads
- churn risk
- product feedback
- investor/category notes
- internal strategy
- noisy newsletters
- irrelevant personal-ish email
- call transcripts
- work-system issues

## Run Locally

From the repo root:

```bash
bash examples/synthetic-corpus/run.sh /tmp/lettuce-synthetic-demo
```

The default run uses the deterministic fallback provider and direct brain writes. It proves stream, handler, brain, checkpoint, log, and git plumbing, but it is not a model-quality judgment. Set `LETTUCE_SYNTHETIC_REVIEW=true` only when you intentionally want optional review-mode plumbing behavior.

For real model judgment:

```bash
LETTUCE_SYNTHETIC_PROVIDER=openclaw \
LETTUCE_OPENCLAW_MODEL="anthropic/claude-haiku-4-5" \
bash examples/synthetic-corpus/run.sh /tmp/lettuce-synthetic-demo-model
```

## Interpreting Results

This corpus is not a benchmark. It is a product QA fixture. Inspect whether Lettuce:

- skips irrelevant or personal-ish noise
- routes account/customer context differently from product discovery
- preserves source provenance
- creates durable `brain/*` markdown outputs, or clear skip/noise logs
- exposes missing handlers, such as a future email normalizer or action router

The `expected_handlers` field in `manifest.json` is an expectation guide, not a strict assertion. Model-backed handler judgment may legitimately skip or publish differently if the note content changes.
