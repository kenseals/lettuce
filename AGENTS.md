# Agents working with Lettuce

Lettuce is an agent-operated, local-first markdown+git protocol for durable company/project context. It is meant to be installed and run by the operator's agent, not learned first by the operator.

Claude Code may read its own project instructions automatically. Everyone else, including OpenClaw, Walm-e, Codex, Cursor, Aider, Continue, or an LLM fetching by URL, should start here.

## Install and setup path

1. Read `llms.txt` for the one-link setup entrypoint and doc map.
2. Read `INSTALL_FOR_AGENTS.md` for the linear agent setup guide.
3. Read `docs/agent-operated-onboarding.md` for the full onboarding contract.
4. Install only after the operator confirms setup:

```bash
python3 -m pip install 'git+https://github.com/kenseals/lettuce.git'
lettuce --help
```

If the shell cannot find `lettuce`, use `python3 -m lettuce.cli ...`.

## Operator experience rule

Do not make the operator learn or run CLI commands when they are onboarding through an agent surface such as Telegram, Slack, iMessage, Discord, web chat, or voice.

Use the CLI yourself if your runtime has shell/tool access. If your runtime does not have shell/file access, say that plainly and guide setup as far as possible.

Good behavior:

```text
I can set this up for you. I’ll ask a few questions, create or choose the repo, configure the first sources, run the first sample through review, then summarize what changed.
```

Bad behavior:

```text
Run these commands on your machine and paste the output.
```

The CLI is the agent's reliable helper for file/git/schema/checkpoint work. It is not homework for the operator.

## Read this order

1. `AGENTS.md` (this file) — operating protocol for agents.
2. `INSTALL_FOR_AGENTS.md` — short linear setup guide.
3. `llms.txt` — one-link setup entrypoint and doc map.
4. `docs/company-context-for-agents.md` — product frame and boundaries.
5. `docs/agent-operated-onboarding.md` — detailed onboarding phases.
6. `docs/source-discovery-recipes.md` — source setup and sampling rules.
7. `HANDLERS.md` and `LETTUCE_V0_SPEC.md` — protocol details if you are changing handlers/runtime behavior.

## Core trust boundary

The agent runtime owns access to the outside world:

- chat surfaces such as Telegram, Slack, iMessage, Discord, browser chat, or CLI;
- email/inboxes and forwarded messages;
- transcript systems and exported files;
- GitHub, Linear, Notion, Slack, docs, CRM, support tools;
- OAuth, API keys, browser sessions, MCP tools, and scheduling.

Lettuce owns durable protocol state:

- repo structure and `lettuce.yml`;
- streams and source records;
- handlers/lenses;
- brain updates;
- review records;
- subscriptions;
- checkpoints and logs;
- git history.

Do not build duplicate chat/email/browser/OAuth surfaces inside Lettuce. Use the runtime's existing access, then write selected signal into Lettuce streams with provenance.

## First setup contract

During first setup:

1. Explain Lettuce in plain English.
2. Confirm the operator wants to continue.
3. Ask which company/client/project this Lettuce is for.
4. Choose or create one org-scoped repo.
5. Configure manual/direct ingestion so the operator can later say “run Lettuce on this.”
6. Record source intent for email/transcripts/work systems as `available_now`, `needs_setup`, `defer`, or manual-only.
7. Ingest one small operator-approved sample signal.
8. Run handlers behind the review gate unless the operator explicitly asks to bypass review.
9. End with a concise handoff: repo path, sources, first run result, future trigger/cadence, and next setup step.

## Common tasks

- **Set up Lettuce:** `INSTALL_FOR_AGENTS.md`, then `docs/agent-operated-onboarding.md`.
- **Smoke test:** `TRY_THIS_FIRST.md`.
- **Human/product overview:** `README.md` and `docs/company-context-for-agents.md`.
- **Source setup:** `docs/source-discovery-recipes.md`.
- **OpenClaw-specific usage:** `skills/openclaw-lettuce/SKILL.md`.
- **Protocol changes:** `LETTUCE_V0_SPEC.md`, `HANDLERS.md`, tests under `tests/`.

## Before shipping repo changes

Run the smallest meaningful gate for the change. For protocol/runtime changes:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile lettuce/*.py
python3 -m lettuce.runtime --smoke
```

For docs-only changes, inspect the rendered/linked files and verify any public raw GitHub URL that will be handed to another agent.

## Maintainer notes for this checkout

Canonical public-launch repo: `https://github.com/kenseals/lettuce`.

When committing to the public repo, use Ken's verified GitHub noreply identity:

```bash
git config user.name "Ken Seals"
git config user.email "505465+kenseals@users.noreply.github.com"
```

Do not use `OpenClaw Server`, `k2claw`, or machine-local email identities for public Lettuce commits.

Old private/internal history may exist at `/Users/oc/.openclaw/workspace/repos/lettuce` and `k2claw/lettuce`. Do not use it as the public launch surface.

Do not make the repo public, create public releases, or announce externally without explicit Ken approval.
