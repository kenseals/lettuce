# Lettuce Installation Guide for AI Agents

Read this file, then follow the steps. Lettuce is meant to be set up and operated by the user's agent. The operator should answer setup questions and approve sensitive boundaries; they should not have to learn the CLI first.

Target: 5-10 minutes to a local git-backed Lettuce repo with one first signal and manual/direct ingestion ready.

## Step 0: Start with the operator, not commands

Briefly explain:

> Lettuce gives your agent a local markdown+git work brain for one company/project. It keeps that work context separate from personal memory, records which sources should feed it, and lets the agent keep the context fresh from signals it can access.

Then ask for confirmation and the minimum setup details:

1. Which company, client, or project is this Lettuce for?
2. Should we start local first, or use an existing repo/path?
3. What signal sources should eventually feed it? Common starters: direct notes, email, meeting transcripts, GitHub/Linear/Notion/Slack, local files.
4. Which sources can you access now, and which should be marked as later/needs setup?
5. What one small meaningful sample signal should calibrate the first run?

If the operator is talking to you in Telegram, Slack, iMessage, Discord, or another chat surface, do **not** ask them to run CLI commands. If your runtime has shell/tool access, run the commands yourself. If you do not have shell/file access, say so plainly and guide the setup as far as your runtime allows.

## Step 1: Read the primary docs

- `llms.txt` is the one-link setup entrypoint and doc map.
- `AGENTS.md` is the public operating protocol for non-Claude agents.
- `docs/agent-operated-onboarding.md` is the detailed setup contract.
- `docs/source-discovery-recipes.md` covers source intent and safe sampling.
- `docs/source-recipes/` contains concrete agent-readable recipes for direct/manual and recurring-ish sources.
- `docs/trust-boundary.md` formalizes trust modes, operation classes, and path mutation rules.
- `docs/LETTUCE_VERIFY.md` is the post-setup verification runbook.
- `docs/LETTUCE_RESOLVER.md` is the ongoing-use resolver after setup.

If you fetched this file by URL, companion files live at:

- `https://raw.githubusercontent.com/kenseals/lettuce/main/llms.txt`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/AGENTS.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/agent-operated-onboarding.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/source-discovery-recipes.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/source-recipes/README.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/source-recipes/direct-manual.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/source-recipes/email-recurring.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/trust-boundary.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/LETTUCE_VERIFY.md`
- `https://raw.githubusercontent.com/kenseals/lettuce/main/docs/LETTUCE_RESOLVER.md`

## Step 2: Install Lettuce

After the operator confirms setup:

```bash
python3 -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

If the shell cannot find `lettuce`, use:

```bash
python3 -m lettuce.cli --help
```

## Step 3: Prefer the guided setup helper when available

If you have an interactive shell, run:

```bash
lettuce setup --commit
```

This helper introduces Lettuce, confirms the operator wants to continue, asks for org/operator/repo/source details, configures manual/direct ingestion, optionally records email and transcript source intent, ingests one first setup signal, runs handlers behind the review gate, and prints a concise final summary.

## Step 4: If needed, run the lower-level flow yourself

Create or choose one org-scoped repo. Do not mix multiple companies/projects into one Lettuce by default.

For the first sample signal, prefer a body file so the operator's exact wording is preserved:

```bash
cat > /tmp/lettuce-first-signal.md <<'EOF'
<operator-approved first signal here>
EOF

lettuce onboard <repo-path> \
  --org <org-slug> \
  --operator <operator-name> \
  --title "First setup signal" \
  --body-file /tmp/lettuce-first-signal.md \
  --source <agent.surface> \
  --surface <surface> \
  --consent operator-direct-request \
  --review \
  --commit
```

Use `--openclaw-provider` only when running inside OpenClaw and model-backed handler judgment is available. Otherwise the deterministic fallback is acceptable for setup smoke tests.

Configure manual/direct ingestion in every normal setup so the operator can later say “run Lettuce on this”:

```bash
lettuce add-source direct <repo-path> \
  --name manual-direct \
  --access-status available_now \
  --sample-policy "operator-forwarded-or-pasted-signals" \
  --commit
```

Treat that direct/manual source as `manual-only` in the recipe sense: operator-triggered, runtime-ingested, not polled. Keep the persisted CLI status truthful, usually `available_now`.

Record other sources as intent, not fake integrations:

```bash
lettuce add-source email <repo-path> --name work-email --access-status needs_setup --setup-next-action "connect forwarding/export before sampling" --commit
lettuce add-source transcript <repo-path> --name calls --access-status defer --setup-next-action "choose transcript source later" --commit
```

## Step 5: Verify the setup

For the full verification runbook, read `docs/LETTUCE_VERIFY.md`. At minimum, run:

Run:

```bash
lettuce status <repo-path>
lettuce logs <repo-path> --limit 5
lettuce reviews <repo-path>
git -C <repo-path> status --short
```

Expected:

- the repo exists and is a git repo;
- the first event exists under `streams/inbox/direct/` with provenance;
- source intent exists for manual/direct and any selected sources;
- review mode created pending review proposals or a clear skip reason;
- no durable `brain/*` update was applied before review approval;
- committed setup leaves a clean git status.

## Step 6: Handoff to the operator

End with a concise summary:

- repo path initialized or reused;
- org/operator scope;
- configured sources and status;
- first event/provenance;
- pending review proposals or skip reason;
- trigger phrase/cadence for future use;
- next source worth connecting or sampling.

Recommended wording:

> Done. I set up Lettuce for <org> at <repo>. Manual/direct ingestion is ready, so you can say “run Lettuce on this” and I’ll capture the signal with provenance, run lenses, and show review proposals before durable brain updates. I recorded <sources> with <status>. Next useful step: <next source/sample>.

## Core boundaries

- Lettuce does not own chat, email, OAuth, browser sessions, or external integrations. Your runtime owns access; Lettuce owns durable protocol state.
- Shared-stream imports belong in scoped mirror paths such as `streams/shared/*`, not directly in `brain/*`.
- Do not bulk ingest during onboarding unless the operator explicitly asks.
- Preserve source provenance, consent basis, source surface, org scope, and operator scope.
- Use review mode during onboarding unless the operator explicitly asks to bypass it.
