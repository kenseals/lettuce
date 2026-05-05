# Lettuce Installation Guide for AI Agents

Read this file, then follow the steps. Lettuce is meant to be set up and operated by the user's agent. The operator should answer setup questions and approve sensitive boundaries; they should not have to learn the CLI first.

Target: 5-10 minutes to a local git-backed Lettuce repo with one first signal and manual/direct ingestion ready.

## Critical: do not turn onboarding into a CLI smoke test

When the operator asks for a clean install, install test, onboarding test, or says they are trying Lettuce from `llms.txt`, your primary job is to test the **public agent-operated onboarding flow**.

A package smoke test is not enough. Do not silently substitute:

- `lettuce onboard ...` with a canned sample signal;
- `lettuce ingest-direct` / `lettuce run` without the setup conversation;
- `examples/quick-demo.sh` or synthetic fixtures;
- global install cleanup or PATH fixes as the “result.”

Those are diagnostic tools after the guided setup path is proven or blocked. The first-pass success criterion is: the operator experienced the explanation, confirmation, setup questions, guided install/setup helper, first approved sample, review gate, and handoff.

## Step 0: Start with the operator, not commands

Briefly explain:

> Lettuce gives your agent a local markdown+git work brain for one company/project. It keeps that work context separate from personal memory, records which sources should feed it, and lets the agent keep the context fresh from signals it can access.

Then ask for confirmation and the minimum setup details **one question at a time**. Show progress, such as `Question 1/5`, and include a short teaching note before each question. First-time operators do not yet know Lettuce's mental model, so every setup question should explain why the answer matters.

1. Which company, client, or project is this Lettuce for?
2. Should we start local first, or use an existing repo/path?
3. What signal sources should eventually feed it? Common starters: direct notes, email, meeting transcripts, GitHub/Linear/Notion/Slack, local files.
4. Which sources can you access now, and which should be marked as later/needs setup?
5. What one small meaningful sample signal should calibrate the first run?

If the operator is talking to you in Telegram, Slack, iMessage, Discord, or another chat surface, do **not** ask them to run CLI commands. If your runtime has shell/tool access, run the commands yourself. If you do not have shell/file access, say so plainly and guide the setup as far as your runtime allows.

Before asking the operator to enumerate sources cold, offer to scan or inspect the sources your runtime can already access. Then walk the operator through source setup one source at a time. For each selected source, explain:

- current access status: `available_now`, `needs_setup`, `defer`, or manual-only posture;
- how/when signal will ingest, such as manual trigger, daily email check, after meetings, or operator-selected samples;
- privacy/sample boundary;
- smallest next setup action;
- whether the source was actually configured or merely recorded for later.

As you perform setup actions, narrate the material ones with a short “what and why.” This includes creating/reusing the repo, writing `LETTUCE_AGENT.md` or runtime skill instructions, configuring each source record, ingesting the first sample, running handlers/review gate, and writing the final handoff. Keep it concise, but do not make the operator infer what changed.

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

The helper should feel like a guided first-run product flow, not a form. It should ask one question at a time, explain non-obvious concepts such as repo path/local-vs-existing, offer source discovery, and summarize source behavior before declaring setup complete.

It should also be transparent about setup actions. A good helper says “I’m configuring manual/direct ingestion so you can later say ‘run Lettuce on this’” before it writes that source record, and “I’m writing repo-local agent instructions so future agents know how to use this Lettuce” before it creates the handoff/instruction files.

If `lettuce setup --commit` fails or is unavailable, stop and report that as an onboarding bug/blocker before falling back. Only use the lower-level flow after explaining the blocker, because otherwise you are no longer testing the intended onboarding experience.

Default to the solo-founder branch. That path should feel lightweight: personal repo, manual/direct ingestion, one source plan, first handler pass, optional GitHub remote later, shared streams mentioned only as future-ready context. Choose the multi-operator branch only when the operator explicitly expects multiple personal or role-agent Lettuces and wants the handoff to record hub/shared-stream intent.

## Step 4: If needed, run the lower-level flow yourself

Use this section for fallback/diagnostics, not as the default clean-install path. If you start here during a public onboarding test, you are skipping the product experience Lettuce is trying to validate.

Create or choose one org-scoped repo. Do not mix multiple companies/projects into one Lettuce by default.

For the first sample signal, prefer a body file so the operator's exact wording is preserved:

```bash
cat > /tmp/lettuce-first-signal.md <<'EOF'
<operator-approved first signal here>
EOF

lettuce onboard <repo-path> \
  --org <org-slug> \
  --operator <operator-name> \
  --onboarding-path solo_founder \
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

If the operator explicitly wants the multi-operator branch, record intent rather than pretending unshipped GitHub org scans or remote shared-stream pulls already exist. The setup handoff should note likely personal, role-agent, and `lettuce-<org>-hub` candidates; future shared imports stay scoped to `streams/shared/*`; and any shared signal must run through local handlers before local brain promotion.

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
- `lettuce status` exposes a `freshness` summary that matches reality: `fresh`, `pending_review`, `blocked_on_setup`, or `idle_manual_only`;
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
