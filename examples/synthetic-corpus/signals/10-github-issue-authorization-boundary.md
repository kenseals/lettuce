# GitHub issue: authorization boundary

Source: synthetic GitHub issue
Repo: northstar-tools/runtime
Issue title: Agent wrote to shared context without policy

A design partner reports that the runtime wrote a new account rule into a shared stream after parsing one support ticket.

Expected behavior: the handler should attach the source ticket, obey the stream policy, and make the update inspectable/reversible. The runtime should not write shared context automatically unless the repo policy says the handler is trusted for that stream.

Suggested acceptance criteria:

- every context update links to source event id
- shared-stream writes are policy-gated
- trusted handlers can be configured explicitly
- audit log shows handler, model/provider, timestamp, and policy/approval basis

This is not just a bug. It clarifies the product boundary between agent suggestion and durable protocol state.
