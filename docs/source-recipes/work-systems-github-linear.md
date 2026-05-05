# Source Recipe: Work Systems / GitHub + Linear

Use this recipe for GitHub issues/PRs/discussions, Linear issues/projects, Notion/docs, Slack channels, or similar work systems. The runtime owns service auth, API calls, browser sessions, MCP, and schedules. Lettuce records the source contract and selected signal events.

This recipe is intentionally sample-first. Work systems can contain a lot of stale, private, or irrelevant state, so first setup should prove a narrow path before any broad scan.

## Runtime Access Required

At least one of:

- existing runtime connector/API/MCP/browser access;
- authenticated CLI such as `gh` for GitHub or an existing Linear tool;
- operator-provided URLs to specific issues/PRs/docs/channels;
- exported markdown/JSON/CSV from the system.

Do not create new OAuth apps, webhooks, bots, or polling jobs inside Lettuce during onboarding. Record `needs_setup` if the runtime cannot inspect a tiny sample yet.

## Operator Questions

Ask one at a time, with context:

1. Which work system should we start with? Examples: GitHub, Linear, Notion/docs, Slack.
2. Which repo/team/project/channel/database is in scope?
3. What kind of signal matters? Examples: decisions, customer requests, bugs, roadmap changes, PR review state, open loops, blockers.
4. Can the runtime access it now, or should we mark it as needs setup?
5. What small sample is safe? Examples: one repo's 3-5 open issues, one Linear project, one PR thread, one docs folder.
6. What should always be skipped? Examples: secrets, private unrelated repos, personal content, noisy activity logs.
7. What trigger/cadence makes sense? Examples: manual, daily issue check, after PR review, before planning, operator-selected only.

## Connection Plan

Use this shared decision order rather than assuming a work-system integration exists:

1. Check existing runtime access first: MCP/tool connector, authenticated CLI, API token, browser session, local export, or operator-provided URLs.
2. Scope tightly before sampling: one repo, team, project, channel, database, folder, query, or URL set.
3. If access exists, sample 3-5 selected items with stable ids/URLs and the query/filter preserved.
4. If access does not exist, record `needs_setup` and the smallest setup step: authenticate the runtime, connect MCP/API, open browser access, or provide selected URLs/exports.
5. Prefer polling/cron for issue/project/channel state unless the source has high-value event notifications and the runtime already has webhook infrastructure.
6. Use webhook only when the runtime can authenticate events, verify signatures when relevant, dedupe by source id, and constrain scope.
7. Use manual-only when the operator wants selected links/exports rather than ongoing access.

The recipe should not try to enumerate every object the work system supports. It should help the agent ask what kind of signal matters, inspect current access, choose webhook vs polling vs manual, and record the real setup state.

## Classification

- `available_now`: runtime can inspect a tiny scoped sample now.
- `needs_setup`: operator must authenticate, connect MCP/API, open browser access, or provide URLs/exports.
- `defer`: useful later, but not worth setup friction during first onboarding.
- `manual-only`: operator will paste URLs, exports, or selected snippets when they want Lettuce to process them.

## Source Record Commands

GitHub available now:

```bash
lettuce add-source github <repo-path> \
  --name product-repo \
  --workspace <owner/repo> \
  --access-status available_now \
  --sample-policy "operator-approved issues/PRs only; start with 3-5 items" \
  --privacy-notes "skip secrets, private unrelated repos, and token-bearing logs" \
  --setup-next-action "sample selected issues/PRs, preserve URLs/ids, then inspect review output before recurring checks" \
  --commit
```

GitHub needs setup:

```bash
lettuce add-source github <repo-path> \
  --name product-repo \
  --workspace <owner/repo> \
  --access-status needs_setup \
  --sample-policy "operator provides 1-3 issue/PR URLs before connector-based sampling" \
  --privacy-notes "skip secrets and unrelated repos" \
  --setup-next-action "authenticate runtime GitHub access or provide selected issue/PR URLs" \
  --commit
```

Linear available now:

```bash
lettuce add-source linear <repo-path> \
  --name product-linear \
  --workspace <team-or-project-label> \
  --access-status available_now \
  --sample-policy "operator-approved project/issues only; start with 3-5 items" \
  --privacy-notes "skip unrelated teams and private HR/legal work" \
  --setup-next-action "sample selected issues/project state before recurring checks" \
  --commit
```

Generic docs/Slack/Notion use the same pattern with `docs`, `slack`, or `notion` as the source type.

## Privacy / Sample Defaults

- Start with 3-5 operator-approved items, or fewer if the system is sensitive.
- Preserve URLs, ids, repo/team/project/channel, author when useful, timestamps, and query/filter used.
- Do not copy secrets, tokens, private logs, or unrelated repo/team context into Lettuce.
- Prefer summarized events over raw dumps when the source content is large or noisy.
- Keep the source record honest: a recorded GitHub source is not the same as a live integration.

## First Tiny Sample Path

For GitHub issue/PR samples, the runtime can fetch selected items, summarize them to a markdown body file, then ingest as work-system signal. Until dedicated work-system ingest commands exist, use `add-event` to `streams/inbox/work`:

```bash
lettuce add-event <repo-path> \
  --stream streams/inbox/work \
  --title "GitHub sample: <owner/repo>" \
  --body-file /tmp/lettuce-github-sample.md \
  --source "github:<owner/repo>" \
  --commit
lettuce run <repo-path> --stream streams/inbox/work --review --commit
lettuce reviews <repo-path>
```

If handlers do not yet subscribe to `streams/inbox/work`, bridge the first sample through `ingest-direct` with explicit GitHub/Linear provenance in the body and record the limitation in the handoff.

## Verification Checks

- `sources/` contains a work-system source record with honest access status.
- Source record states repo/team/project/channel scope, sample policy, privacy boundary, cadence/trigger, and next setup action.
- Any sample event preserves source URLs/ids and query/filter provenance.
- Review output is useful before recurring checks or broad scans are proposed.
- Handoff says whether the source is actually configured, needs setup, deferred, or manual-only.

## Operator Handoff

Example:

> I recorded GitHub for `<org>` as `<available_now|needs_setup|defer>` for `<owner/repo>`. This does not ingest all repo activity. The first sample path is `<selected issues/PRs | operator-provided URLs | needs auth>`, with `<privacy boundary>`. If we make it recurring, the runtime will own the check schedule and Lettuce will preserve source records, events, reviews, and brain updates.
