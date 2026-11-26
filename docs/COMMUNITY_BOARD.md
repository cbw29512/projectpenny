# Penny's Command Center — suggestion intake and work board
Approved goal: Penny works toward commercial success and remains welcoming.
Community ideas are private until reviewed; no direct task or tool execution.

## State and schema
Community suggestion: UUID, authenticated member UUID, idempotency key,
bounded normalized text, SHA-256 duplicate key, DB timestamp, policy version.
Review: immutable single terminal decision bound to exact suggestion digest,
trusted reviewer, fixed reason, timestamp and policy version. States:
pending -> eligible / rejected / deferred. Eligible means candidate backlog,
not permission to schedule, publish, spend, or execute. Deferred reconsideration
will require an explicit later review contract. Never publish private text.
Use existing member session resolution and scheduler transaction lock.
No model calls during intake. No raw suggestions in logs, public snapshots,
memory or executable prompts. Every input remains untrusted even after review.

## Intake limits
500 characters before and after normalization; reject invisible controls,
empty/low-content input, and invalid key. Per authenticated owner: three new
ideas in rolling 24 hours, three pending. Global: 60/day, 100 pending,
4096 retained records. Exact owner-scoped duplicate is idempotent, including
case/spacing variants. Never reveal another owner's submissions. All counts
and inserts atomic; fail closed at capacity. Cross-owner near-duplicate and
semantic moderation are later bounded review stages, not claimed here.
Retention, erasure, public edge controls and identity provider integration
are mandatory before public intake. No public HTTP route in this increment.

## Work board and hourly planning (next increments)
Reuse work_task, business opportunity/event, approval and outcome evidence.
Project verified lanes: community inbox (aggregate only), evaluating,
backlog, scheduled, in progress, awaiting Maker, testing, completed,
rejected/deferred. Do not equate a successful draft with completed business.
Hourly planner selects at most one eligible bounded task, with durable
hour-slot idempotency, objective, deadline, evidence and safe checkpoint;
never bypass pause, Guardian, capacity, fairness or approval. No guaranteed
hourly activity: record skipped/blocked states honestly. Daily standup
summarizes reviewed outcomes and current blockers, not model inventions.
Review assistant may later suggest mission/revenue/feasibility/cost/community/
originality scores (25/25/20/15/10/5), but scores are advisory. Legal,
security, evidence and Maker review gates cannot be bypassed. Treat nonsense
as defer/reject, retain humorous legitimate ideas. No keyword list is proof
of safety. Voting and consented contributor recognition follow verified
outcomes via existing recognition contracts. Never expose raw rejected text.

## First private hourly planner slice
Migration 032 adds an immutable UTC-hour decision record. A trusted operator
calls plan_hour with explicit confirmation and reviewer identity. Under the
existing scheduler transaction lock, replay the same slot, check pause and
inference gates, skip any live queue work, and select only an already
Maker-approved and started digital-product experiment with no prior workshop
task. Reuse workshop admission and its quotas/deadline. Commit the decision
and queued task together; one decision per hour, even when skipped. Failed
transactions leave no slot record and may be retried. Prior prototypes,
including invalid outputs, require independent review, not automatic retries.
This is a private adapter, not a timer, public board or general-purpose agent.
No software utility implementation, new ideas, spending, publication, approval,
measurement or external actions. Runtime permissions and timer deployment
remain separate acceptance gates.
