# Durable queue slice v0.1
Objective: persist accepted work and claim only one running task across competing processes. This is an internal repository API, not a public endpoint.

## State
PostgreSQL 16 schema migration 001 defines scheduler_control, scheduler_entitlement, work_task, task_outcome. UUID task/member identifiers, integer UTC epoch seconds, null member for internal work. Entitlements are provisioned only by a trusted administrator, not request parameters. The provider verification pipeline is not yet implemented. One running row enforced by a partial unique index. Scoped idempotency key remains unique even after task completion.
Task transitions: queued -> running -> succeeded/failed; queued -> expired/canceled. Expired running work remains locked until an authorized supervisor confirms the previous process and inference request are stopped. Recovery records failure rather than automatically rerunning a potentially executed operation.

## Logic
Every mutation obtains the singleton row lock at READ COMMITTED isolation before reading queue state. Admission checks existing idempotency key and matching payload, expires old queued work, resolves current entitlement and applies the shared policy. Admission commits before acknowledgement. Dispatch rechecks entitlements; changed tiers cancel waiting work (member may resubmit with new key), avoiding implicit class-cap overflow. Compute usage uses completed task wall time as a provisional proxy over the last 24 hours.
Claim sets unique fence token and bounded lease (120 seconds public, 900 business; capped by deadline). Completion requires matching token, running state and valid lease. Outcome, usage and last-served member commit together. Expired claims are never automatically stolen. Recovery requires explicit operator confirmation and the matching expired fence. No actual external effects or worker yet.
All API callers are trusted internal code; no public authentication or payment integration. Daily quotas, checkpoints, cancellation of active work, notifications, retention, measured GPU usage, safe worker isolation automation and retry policy remain follow-up tasks. No runtime guarantee until worker enforcement is built.
Run integration tests only with a disposable PostgreSQL database. Never point the tests at production.
