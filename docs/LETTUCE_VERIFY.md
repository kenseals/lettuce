# Lettuce Installation Verification Runbook

Run these checks after first setup to confirm Lettuce is actually usable. "Setup ran" is not the same as "Lettuce is ready." A setup that creates files but does not preserve provenance, review state, source intent, or future trigger behavior is worse than no setup because the operator thinks durable context exists when it does not.

Target: verify one org-scoped Lettuce repo, one first signal, one safe review loop, and one clear ongoing trigger.

## 1. Repo and config exist

Command:

```bash
lettuce status <repo-path>
git -C <repo-path> status --short
find <repo-path> -maxdepth 2 -type f | sort | head -80
```

Expected:

- `<repo-path>` exists.
- `<repo-path>/.git/` exists.
- `lettuce.yml` or equivalent repo config exists.
- `streams/`, `handlers/`, `.lettuce/`, and usually `sources/` exist.
- If setup used `--commit`, git status is clean or only contains intentionally uncommitted operator edits.

If it fails:

- If the repo does not exist, setup never completed. Re-run `lettuce setup --commit` or the lower-level `lettuce onboard ... --commit` flow.
- If git status is dirty after committed setup, inspect the diff before continuing. Do not hide dirty state from the operator.

## 2. Org/operator scope is correct

Inspect repo config and setup logs:

```bash
lettuce status <repo-path>
lettuce logs <repo-path> --limit 10
```

Expected:

- The org/project/client name matches what the operator intended.
- The operator name/handle is present when supported.
- The repo is scoped to one work context, not a mix of personal memory and multiple unrelated orgs.

If it fails:

- Stop and correct scope before ingesting more signal.
- Do not bulk-ingest into the wrong org. Create a new repo if the contexts should be separate.

## 3. First event exists with provenance

Command:

```bash
find <repo-path>/streams -type f | sort | head -20
```

Open the first direct/input event and check frontmatter/body.

Expected:

- At least one event exists under a stream such as `streams/inbox/direct/`.
- The event has a meaningful title/body from an operator-approved sample signal.
- Provenance fields are present where supported: source, surface, consent basis, observed time, sender, message/thread id, file path, or equivalent.
- The setup request itself was not used as the first signal unless the operator explicitly approved that.

If it fails:

- Ingest one small real sample with `lettuce ingest-direct` or `lettuce onboard --body-file`.
- Preserve exact operator wording in a temp body file for multi-paragraph samples.

## 4. Manual/direct source is ready

Command:

```bash
find <repo-path>/sources -maxdepth 2 -type f -print -exec sed -n '1,120p' {} \;
```

Expected:

- There is a source record for manual/direct/operator-forwarded signal, or an equivalent repo-local instruction.
- It says the trigger behavior clearly, for example: operator can say “run Lettuce on this.”
- It records a truthful CLI `access_status` such as `available_now` and explicitly says the source is manual-only/operator-triggered in the source record text or sample policy.

If it fails:

```bash
lettuce add-source direct <repo-path> \
  --name manual-direct \
  --access-status available_now \
  --sample-policy "operator-forwarded-or-pasted-signals" \
  --commit
```

Then tell the operator the trigger phrase/cadence.

## 5. Other source intent is honest

Inspect source records for email, transcripts, GitHub/Linear/Notion/Slack, local files, or other work systems.

Expected:

- Each candidate source has a truthful CLI `access_status` such as `available_now`, `needs_setup`, `defer`, or `unknown`, plus any manual-only/operator-triggered behavior called out in the source record when relevant.
- The setup next action is specific when setup is needed.
- The record does not pretend OAuth, polling, forwarding, or webhook access exists when the runtime does not actually have it.
- No bulk ingestion happened during first setup unless the operator explicitly asked.

If it fails:

- Edit or recreate the source record with the honest current status.
- Prefer a tiny sample path over broad ingestion.

## 6. Review gate behaved correctly

Command:

```bash
lettuce reviews <repo-path>
find <repo-path>/reviews -type f | sort | head -50
find <repo-path>/brain -type f | sort | head -50
```

Expected during onboarding:

- If setup used review mode, handler output created pending review proposals or a clear skip reason.
- No durable `brain/*` update was applied before review approval.
- Pending review files are understandable enough for the operator/agent to approve, edit, or decline.

If it fails:

- If `brain/*` was written before approval while review mode was requested, treat it as a bug.
- If there are no reviews and no skip reason, rerun with `lettuce run <repo-path> --review --commit` and inspect logs.

## 7. Approve/decline loop works

Pick one review proposal and approve or decline it based on operator preference.

Command:

```bash
lettuce reviews <repo-path>
lettuce review-approve <repo-path> <review-id> --operator <operator> --commit
# or
lettuce review-decline <repo-path> <review-id> --operator <operator> --reason "not useful" --commit
```

Expected:

- Approve publishes the reviewed body to its target `brain/*` stream.
- Decline archives the proposal without publishing.
- Logs/checkpoints record the action.
- Git status is clean after committed review action.

If it fails:

- Capture `lettuce logs <repo-path> --limit 20` and `git -C <repo-path> status --short`.
- Do not continue to recurring ingestion until the review loop is trustworthy.

## 8. Runtime handoff is explicit

Ask the agent/operator-facing setup summary to include:

- repo initialized or reused;
- org/operator scope;
- configured sources and their status;
- what first event was ingested;
- what review proposals were created or skipped;
- how the operator triggers future manual/direct use;
- whether any recurring cadence exists;
- the next useful source to connect or sample.

Expected:

- The operator can explain in one sentence what Lettuce will do next.
- There is no vague promise like “I’ll keep this updated” without a concrete trigger, cron, or manual instruction.

If it fails:

- Write a concise handoff before ending setup.
- If recurring checks are not configured, say so plainly: “Manual/agent-triggered for now.”

## 9. Ongoing signal smoke test

After setup, test the future trigger with one new small signal.

Command shape:

```bash
cat > /tmp/lettuce-followup-signal.md <<'EOF'
<new operator-approved signal>
EOF

lettuce ingest-direct <repo-path> \
  --title "Follow-up signal" \
  --body-file /tmp/lettuce-followup-signal.md \
  --source <agent.surface> \
  --surface <surface> \
  --consent operator-direct-request \
  --commit
lettuce run <repo-path> --review --commit
lettuce reviews <repo-path>
```

Expected:

- A second event appears with correct provenance.
- Handler output creates a review proposal or a clear skip reason.
- The operator-facing “run Lettuce on this” behavior is proven, not merely documented.

## 10. Final health bundle

For handoff/debugging, capture:

```bash
lettuce status <repo-path>
lettuce logs <repo-path> --limit 10
lettuce reviews <repo-path>
git -C <repo-path> status --short
```

A clean first install should end with:

- correct org scope;
- direct/manual ingestion ready;
- source intent records honest;
- one first signal with provenance;
- pending/approved/declined review state inspectable;
- git-backed committed state;
- a clear next trigger or cadence.
