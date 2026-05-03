# Public v0 Release Checklist

Goal: ship a public v0 that proves Lettuce as an agent-operated markdown+git protocol, not a finished hosted app.

## Public v0 promise

An operator can ask their agent to set up a Lettuce repo, ingest one approved signal sample, run markdown handlers, review proposed brain updates, approve or decline them, and keep the result in git.

## Ready now

- Personal Lettuce repo scaffold: `lettuce init` and `lettuce onboard`.
- Markdown handler discovery and execution.
- Agent direct input ingest with provenance and consent fields.
- Operator-forwarded email ingest with email-shaped provenance.
- Source setup/status records for email, transcripts, direct surfaces, and future services.
- Checkpointed local directory source import for repeatable sample-first source ingestion.
- Local shared-stream subscription simulation with provenance, checkpoints, and local stream policy gates.
- Optional OpenClaw model-backed handler provider.
- Native review gate: `--review`, `reviews`, `review-approve`, `review-decline`.
- Synthetic public-safe signal corpus for repeatable QA.
- Fresh install smoke with installed `lettuce` console script.

## Must pass before public v0

- Fresh install quickstart passes from a clean venv using `pip install .` and the review-required path.
- `python3 -m unittest discover -s tests` passes.
- `python3 -m py_compile lettuce/*.py` passes.
- `python3 -m lettuce.runtime --smoke` passes.
- Synthetic corpus deterministic runner passes.
- One OpenClaw-provider dogfood run produces review proposals, not direct brain writes.
- README and QUICKSTART describe agent-owned surfaces clearly and do not imply Lettuce owns Telegram, Gmail, Zoom, Fathom, Granola, or OAuth.
- PR #3 is reviewed for accidental private data, stale app-first claims, commands that require unavailable credentials, and archive boundaries for historical docs.

## Should pass before public v0

- A clean temp repo can approve one review and decline one review with clean git status afterward.
- `reviews --status all` shows pending/approved/declined records coherently.
- At least 3 synthetic signals are inspected manually for judgment quality, including one skip/noise case.
- The repo-packaged OpenClaw skill uses `--review` during onboarding.

## Explicitly deferred

- Hosted SaaS runtime.
- First-party Telegram/iMessage/Discord adapters.
- Real Gmail/Zoom/Fathom/Granola OAuth or polling.
- Remote GitHub shared brain polling and GitHub-team policy mapping.
- Linear side-effect execution.
- Auto-approval policies.

## Current status: public-v0 candidate, final ship gates remain

The core protocol loop is merged to `main` and usable for internal dogfood. Fresh install review-mode smoke has passed, the repo-packaged OpenClaw skill uses the native review gate, and OpenClaw-provider review-mode dogfood produced pending reviews before approval. A clean `git+https://github.com/kenseals/lettuce.git` install also succeeded while the private repo is accessible to this operator environment. Older app-first/runtime-preview docs are not included in the public v0 repo. Packaging has been fixed for legacy pip installs, and the first-use handoff docs exist.

As of the latest local check, the repo is private, has no GitHub release, and has no open PRs. The main remaining public-v0 risk is not core functionality; it is first-user experience and public packaging.

### Must do to ship public today

- Re-run the final clean install/onboarding/usage path only if more launch-path code changes land.
- Verify the repo contains no private operator/workspace context in public-facing files.
- Decide whether public v0 ships as a public GitHub repo only or also with a tagged GitHub release.
- Make the GitHub repo public after final operator approval.
- Add a short launch note / first public issue list that says what works, what is intentionally deferred, and how to try it.

### Nice but not blocking

- Parallelize model-backed handler execution or choose a faster default model for OpenClaw-backed runs.
- Add a tiny screencast/Loom or GIF.
- Add GitHub topics and tighten repo description.
- Add a one-command demo script for the clean public quickstart.
