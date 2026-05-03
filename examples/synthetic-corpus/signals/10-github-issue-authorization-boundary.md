# GitHub issue: authorization boundary

Source: synthetic GitHub issue
Repo: northstar-tools/runtime
Issue title: Agent wrote to shared context without approval

A design partner reports that the runtime wrote a new account rule into shared context after parsing one support ticket.

Expected behavior: the handler should propose the account rule, attach the source ticket, and wait for operator approval. The runtime should not write shared context automatically unless the repo policy says the handler is trusted for that stream.

Suggested acceptance criteria:

- every context update links to source event id
- default mode is review-required
- trusted handlers can be configured explicitly
- audit log shows handler, model/provider, timestamp, and operator decision

This is not just a bug. It clarifies the product boundary between agent suggestion and durable protocol state.
