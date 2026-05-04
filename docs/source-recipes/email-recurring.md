# Source Recipe: Email / Recurring-ish

Use this recipe for operator-selected threads, mailbox searches, labels/folders, forwarded messages, or later recurring mailbox checks. The runtime owns mailbox access and any Gmail/IMAP/OAuth/browser setup; Lettuce only records the contract and resulting events.

## Runtime Access Required

At least one of:

- connected mailbox or Gmail-style connector access;
- provider API or IMAP access already owned by the runtime;
- operator-forwarded emails or exported `.eml` / `.mbox` / markdown email files;
- operator-present browser access to the mailbox.

Do not build new mailbox infrastructure inside Lettuce. If access does not already exist, record `needs_setup` and guide the smallest external setup step.

## Operator Questions

- Which mailbox, account, label, folder, or saved search is in scope?
- What kind of email matters: customer, internal decisions, vendor, support, recruiting, reference/newsletter?
- What privacy boundary applies: personal, family, legal, medical, finance, recruiting, or unrelated org mail?
- Should the first sample be operator-forwarded mail, a mailbox query, or a small label/folder slice?
- If this becomes recurring later, what owns the trigger: manual checks, a daily runtime task, or operator request?

## Classification

- `available_now`: the runtime can already search or read a small sample now.
- `needs_setup`: the runtime still needs forwarding, OAuth, export, connector enablement, or operator-present browser access.
- `defer`: useful later, but not worth setup friction during first onboarding.
- `manual-only`: the runtime cannot poll yet, but the operator can forward or point to specific emails now.

When the posture is manual-only, persist a truthful `access_status` such as `available_now` plus a `sample_policy` that says sampling is operator-forwarded/manual-only.

## Source Record Command

Available now:

```bash
lettuce add-source email <repo-path> \
  --name work-email \
  --address <mailbox-or-account-label> \
  --query "<label-or-query-if-used>" \
  --access-status available_now \
  --sample-policy "first-3-operator-approved messages before any recurring check" \
  --privacy-notes "skip personal, legal, medical, recruiting, finance, and unrelated org mail" \
  --setup-next-action "sample a tiny scoped slice and inspect review output before any backfill" \
  --commit
```

Needs setup:

```bash
lettuce add-source email <repo-path> \
  --name work-email \
  --address <mailbox-or-account-label> \
  --access-status needs_setup \
  --sample-policy "operator-forward one safe example before connector-based polling" \
  --privacy-notes "skip personal and other out-of-scope mail" \
  --setup-next-action "connect mailbox access, export one message, or forward one sample thread" \
  --commit
```

## Privacy / Sample Defaults

- Start with 1-3 operator-approved messages or one thread, not a full mailbox pull.
- Preserve subject, sender, message id, thread id, mailbox/account label, source URL when available, and consent basis.
- Keep redaction notes explicit when sender/recipient details are sensitive.
- If in doubt, prefer operator-forwarded mail first because it makes consent and relevance obvious.

## First Tiny Sample Path

Fastest safe path when mail is already available:

```bash
lettuce ingest-email <repo-path> \
  --subject "<email subject>" \
  --body-file /tmp/lettuce-email-sample.md \
  --message-id <message-id> \
  --thread-id <thread-id> \
  --from "<sender>" \
  --forwarded-by <operator> \
  --consent operator-forwarded-email \
  --commit
lettuce run <repo-path> --review --commit
lettuce reviews <repo-path>
```

If direct mailbox metadata is not available yet, ingest one exported or forwarded email first, then update the source record once recurring access is real.

## Verification Checks

- `sources/` contains an email source record with an honest `access_status`.
- The source record states the mailbox/query boundary, sample policy, privacy boundary, and next setup step.
- `streams/inbox/email/` contains only the tiny approved sample, with email-specific provenance preserved.
- Review output is intelligible before any recurring schedule or backfill is proposed.
- Any recurring cadence is described as runtime-owned, not something Lettuce provisions itself.

## Operator Handoff

Example:

> I recorded the email source for `<org>` at `<repo-path>` with status `<available_now|needs_setup|defer>`. The first sample path is `<forwarded mail | label/query sample | export file>`, and I only sampled `<n>` message(s). If we keep this source recurring, the runtime will own the mailbox access and schedule; Lettuce will keep the durable source contract and provenance.
