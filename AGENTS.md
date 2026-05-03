# AGENTS.md - Lettuce public repo

This checkout is the canonical public-launch repo for Lettuce.

## Canonical GitHub repo

- Public-launch repo: `https://github.com/kenseals/lettuce`
- Local canonical checkout: `/Users/oc/.openclaw/workspace/repos/lettuce-public`
- Use GitHub issues on `kenseals/lettuce` for future improvements, bugs, and launch follow-up.

## Commit identity

Use Ken's verified GitHub noreply identity for this public product repo:

```bash
git config user.name "Ken Seals"
git config user.email "505465+kenseals@users.noreply.github.com"
```

Do not use `OpenClaw Server`, `k2claw`, or machine-local email identities for public Lettuce commits.

## Old private/internal repo

`/Users/oc/.openclaw/workspace/repos/lettuce` and `k2claw/lettuce` are old private/internal history. Do not use them as the public launch surface. The old checkout's push URL has intentionally been disabled to reduce accidental pushes.

Use the old repo only for archaeology if needed, then port intended changes into this canonical public repo.

## Public-release boundary

The repo may be private while testing. Do not make it public, create public releases, or announce links externally without explicit Ken approval.
