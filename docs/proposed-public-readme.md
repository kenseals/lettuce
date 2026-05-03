# Lettuce

> *Pronounced lattice.*
>
> An open protocol for company context in the agentic era. Your agent goes everywhere with you — work, life, every org you touch. Lettuce gives it a place to keep work-context that's yours, in your repos, separable from your personal life, and gets dramatically better the more your teammates run it too.

---

## What this is

You're going to spend more and more of your work running through an agent. That agent needs a place to keep work-context that is:

- **Yours.** In your git repo, in markdown, ownable and editable by you.
- **Portable.** Works with whatever agent you use today and whatever you switch to next year.
- **Separable.** Distinct from your personal life, distinct from other organizations you're part of.
- **Coordinatable.** Can talk to your teammates' agents when you want, without merging into one big company-wide vault.

Lettuce is that place. It's a small open protocol — markdown handlers, git streams, simple policies — that any agent can run.

It ships today as an OpenClaw installer. The protocol is just markdown and git, so any agent that can read files and call tools can be a runtime.

---

## Quick start

If you have OpenClaw set up, point it at this repo:

```
# in your OpenClaw
install lettuce from github.com/<your-handle>/lettuce
```

Your OpenClaw will:

1. Ask which organization you're setting up Lettuce for
2. Create a private GitHub repo for your personal Lettuce (handlers, brain, streams)
3. Check whether anyone at your company already has a shared Lettuce stream — and offer to subscribe or create one
4. Wire up the signal sources you authorize (email, transcripts, direct input)
5. Run the pipeline on a schedule and on demand

Setup takes 5–15 minutes, mostly OAuth. [Loom: end-to-end install + first signal ingest →](#)

---

## For solo operators: keep work in its place

Each Lettuce is scoped to one organization. **One agent, many hats — but no bleed between them.**

Your context for Acme stays in your Acme Lettuce. Your context for your side project stays in its own Lettuce. Your personal life stays in your agent's general memory, untouched.

One repo per `(operator × org)`. Working at one company? You have one Lettuce. Advising three? You have three. They never mix.

---

## For teams: better with every teammate who installs it

A solo Lettuce is useful from day one. The interesting thing happens when a teammate runs one too — and then a few more — and your company quietly accumulates a coordination layer no one had to centralize.

### Stage 01 — Just you

Your agent has structured work-context for one org. It reads your email, knows your customers, tracks decisions, files tickets. **Useful from day one** without anyone else involved.

> *Unlocked: a personal company brain.*

### Stage 02 — A teammate joins

They install Lettuce too. Now your agents can subscribe to each other's shared streams — **the customer your teammate's been talking to becomes visible to your agent**. Without anyone forwarding emails or copying notes.

> *Unlocked: cross-role context for free.*

### Stage 03 — Your whole company

A dozen agents, each mirroring their operator's actual access, federating through shared streams governed by GitHub permissions and editorial policies. **No one has to centralize.** No one's agent ingests everything. The company gets the benefit of shared context without the cost of a vault.

> *Unlocked: federated context for the whole org.*

v0 ships single-operator polished. Multi-operator coordination is supported by the protocol and improving fast.

---

## The protocol

Three primitives. All markdown. All forkable. No proprietary DSL.

### Lenses — interpret signal

Markdown handlers that interpret incoming signal. Lenses don't *do* — they *notice*. Three ship by default:

- **`default-lens.md`** — generalist; surfaces anything notable.
- **`discovery-lens.md`** — continuous-discovery posture; flags product and business opportunities.
- **`accounts-lens.md`** — watches for customer signal worth recording or acting on.

Add your own. A `decisions.md` lens that maintains a decision ledger. A `competitive.md` lens that watches for market moves. Whatever your work needs to notice.

### Routers — commit signal

Markdown handlers that take interpreted signal and produce side effects. One per destination:

- **`brain-router.md`** — decides what gets committed to the brain repo and where.
- **`linear-router.md`** — decides whether to file a triage issue, update an existing one, or do nothing.
- Bring your own: CRM, Notion, Slack, GitHub Issues, calendar, anything with an API.

### Streams — git, all the way down

Git directories of structured markdown events. Three kinds:

- **Inbox streams** — incoming signal, normalized.
- **Brain streams** — interpreted, durable context. Long retention.
- **Outbox streams** — events queued for routers.

Streams live in your personal repo (private) or in shared company repos (cross-team). Subscribing is `git pull`; publishing is `git commit + push`. That's the whole transport layer.

*Your repos. Your permissions. Your runtime.*

---

## How it fits together

```
signal source ─→ inbox stream ─→ lenses ─→ brain stream ─→ routers ─→ services
                                              │
                                              ↓
                                       (your durable
                                        work-context)
```

Each step is a markdown handler. The orchestration is your agent. No bespoke runtime, no SaaS to sign up for, no infra you have to run.

---

## What's in your Lettuce repo

```
lettuce-{org}-{your-handle}/
├── lettuce.yml          # marker + config
├── handlers/
│   ├── lenses/          # interpret signal
│   └── routers/         # commit signal
├── brain/               # durable interpreted context
│   ├── customers/
│   ├── strategy/
│   └── decisions/
└── streams/
    ├── inbox/           # incoming signal
    └── outbox/          # outbound to services
```

Your handlers, your brain, your streams — all in one git history. Backup, migrate, audit, fork: all one operation.

---

## Permissions

Lettuce doesn't manage permissions. It inherits them.

- **Service permissions** come from the OAuth scopes you grant your agent. Your agent can only see what you can see.
- **Repo permissions** come from GitHub. Private brain → private repo. Shared company brain → org repo with org-level access controls.
- **Editorial policies** in `lettuce.yml` declare ownership rules within shared streams (who writes to `decisions/` vs `customers/` vs `incidents/`). These augment GitHub permissions but never override them.

We're not building IAM. We're using yours.

---

## Why markdown, why git

The substrate matters more than the syntax.

- **Markdown is human-legible.** Everything you might want to read, edit, fork, or version-control is markdown. You can open your brain in a text editor and understand it.
- **Git is the right runtime for v0.** It gives you durability, versioning, permissions, audit, forkability, and disaster recovery for free. Streams are git directories. Publishing is a commit. Subscribing is a pull. Boring on purpose.
- **Both are agent-friendly.** Any agent that can read files and call tools can participate in the Lettuce protocol. No new wire format to standardize, no new API to integrate.

At company scale, the runtime will need real-time event delivery and derived indexes underneath. Markdown stays the canonical representation; the optimizations are runtime concerns. v0 is honest about being git-and-markdown all the way down.

---

## Why this exists

When everyone has the same models, **context is the moat.** The bottleneck for AI usefulness inside a company is no longer model capability — it's whether your operating context is legible to an agent.

Most "company brain" products are RAG over documents. That's search, not memory. It tells you what was written; it doesn't tell an agent how your work actually happens.

Lettuce bets differently:

- **Operator sovereignty.** Your data, your repos, your runtime. We don't host signal.
- **Markdown legibility.** Authorable by the operators who hold the knowledge, not just engineers.
- **Inheritance over invention.** Permissions from OAuth and GitHub. Storage from git. Identity from your existing accounts. We use what's already there.
- **Open ecosystem.** Lenses and routers are markdown — anyone with an opinion can contribute, fork, or improve them.

The architecture under the hood — handlers reading from streams and publishing to streams, governed by policies — is event-driven architecture made *legible to humans and editable as text*. The novelty isn't in the pattern. It's in the substrate.

---

## Roadmap

**Now (v0).** OpenClaw-operated install. Default lenses + routers. Brain template. Agent-operated ingestion for direct input, email, and call transcripts. One outbound (Linear). Single-operator polished; multi-operator works but isn't the spotlight feature.

**Next.** Adapters for Claude Code, Codex, and other agent runtimes. More signal sources (Slack, GitHub, Notion). More routers. Polished multi-operator coordination with conflict surfacing. A community-contributed handler marketplace.

**Later.** Self-hostable runtime that doesn't depend on OpenClaw. Webhook-driven event delivery. Derived indexes for fast querying.

**Hosted tier.** Managed stream infrastructure with reliability, scale, identity, audit, and observability — for teams that don't want to self-host. Enterprise features (SSO, on-prem, compliance). Open-core: self-host stays free forever; the hosted tier is what teams pay us for once multi-agent deployments mature.

---

## Status

v0. Built and used in production by the founder. Open-sourced because the protocol layer should belong to the people building on it.

If you're running Lettuce in your own work, I want to hear about it. Issues and PRs welcome.

---

## License

MIT. The protocol, framework, and reference implementation are open. The future hosted tier will be a separate, paid product — the open layer is not going anywhere.
