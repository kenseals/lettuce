# Public v0 Release Checklist

Goal: ship a public v0 that proves Lettuce as an agent-operated markdown+git protocol, not a finished hosted app.

## Public v0 promise

An operator can ask their agent to set up a Lettuce repo, ingest one approved signal sample, run markdown handlers, write useful brain updates with provenance, and keep the result in git.

Optional review mode exists for calibration, sensitive updates, or explicit approval gates. It is not the default product loop.

## Ready now

- Personal Lettuce repo scaffold: `lettuce init` and `lettuce onboard`.
- Markdown handler discovery and execution.
- Agent direct input ingest with provenance and consent fields.
- Operator-forwarded email ingest with email-shaped provenance.
- Source setup/status records for email, transcripts, direct surfaces, and future services.
- Checkpointed local directory source import for repeatable sample-first source ingestion.
- Subscription records plus local export-policy and local-stream policy validation for shared streams.
- Optional OpenClaw model-backed handler provider.
- Optional review mode: `--review`, `reviews`, `review-approve`, `review-decline`.
- Synthetic public-safe signal corpus for repeatable QA.
- Fresh install smoke with installed `lettuce` console script.

## Must pass before public v0

- Fresh install quickstart passes from a clean venv using the first-run path.
- `python3 -m unittest discover -s tests` passes.
- `python3 -m py_compile lettuce/*.py` passes.
- `python3 -m lettuce.runtime --smoke` passes.
- Synthetic corpus deterministic runner passes.
- One OpenClaw-provider dogfood run produces direct brain updates with provenance and git history.
- README and QUICKSTART describe agent-owned surfaces clearly and do not imply Lettuce owns Telegram, Gmail, Zoom, Fathom, Granola, or OAuth.
- Public-facing files are checked for accidental private data, stale app-first claims, commands that require unavailable credentials, and archive boundaries for historical docs.

## Should pass before public v0

- A clean temp repo can run optional review mode, approve one review, and decline one review with clean git status afterward.
- `reviews --status all` shows pending/approved/declined records coherently.
- At least 3 synthetic signals are inspected manually for judgment quality, including one skip/noise case.
- The repo-packaged OpenClaw skill uses direct brain updates by default and documents optional review mode only as a safety/calibration path.

## Explicitly deferred

- Hosted SaaS runtime.
- First-party Telegram/iMessage/Discord adapters.
- Real Gmail/Zoom/Fathom/Granola OAuth or polling.
- Remote GitHub shared-stream polling or pull/mirror execution.
- GitHub-team policy mapping and broader shared-stream policy verification.
- Linear side-effect execution.
- Auto-approval policies.

## Current status: public-v0 candidate, public repo live

The core protocol loop is merged to `main` and usable for internal dogfood. Fresh install smoke has passed, the repo-packaged OpenClaw skill now uses direct brain updates by default, and OpenClaw-provider dogfood should write brain entries without making the operator approve every signal. Older app-first/runtime-preview docs are not included in the public v0 repo. Packaging has been fixed for legacy pip installs, and the one-link first-use handoff docs exist.

The GitHub repo is public. There is no GitHub release yet. The main remaining public-v0 risk is not core functionality; it is first-user experience and alignment with the company-context-for-agents product promise.

### Must do before wider announcement

- Re-run the final clean install/onboarding/usage path after launch-path code/doc changes land.
- Verify the repo contains no private operator/workspace context in public-facing files.
- Keep GitHub Releases/tags off until explicitly approved.
- Track spec-alignment gaps as GitHub issues.

### Nice but not blocking

- Parallelize model-backed handler execution or choose a faster default model for OpenClaw-backed runs.
- Add a tiny screencast/Loom or GIF.
- Add GitHub topics and tighten repo description.
- Add a one-command demo script for the clean public quickstart.
