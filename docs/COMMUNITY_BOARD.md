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

## Private suggestion review and owner status
Bounded oldest-first worklist (maximum 20) and authenticated owner-only
status lookup now share existing intake and terminal review records. No
new scheduling authority, public text, or cross-owner access. Trusted local
operator: `python -m penny.runtime.community --config PRIVATE_CONFIG list`;
review requires exact digest, verdict/reason, reviewer UUID and --confirm.
Retained text remains immutable; retention/erasure and typed cloud transport
must be addressed before public suggestions. CI pending; no live deployment.

Review admission also rejects future or negative submission times and refuses replay of a review outside its submission-to-current-time interval. Regression verification pending CI.

Intake replay validates original content digest, duplicate digest and submission chronology before returning an existing receipt. Corrupted rows return denied without exposing an ID. CI verification pending.

## Community wire candidate
A separate Node validator accepts only a UUID request key and bounded idea text.
No supplied owner, role, tier or command. Local screening remains authoritative;
Unicode behavior must be cross-runtime tested before activation. No HTTP route,
mailbox storage, identity mapping or publication is enabled by this slice.

## Cloud admission candidate (012)
Independent default-off gate and bounded suggestion table. Owner comes from trusted server identity; exact request replay, rolling 3/member and 60/global daily limits, 100 unexpired and 512 retained rows. One-hour expiry. SQL is invoker-only with PUBLIC access revoked; no runtime grants. Local shared feedback quota and screening remain authoritative. No claim, delivery, owner status, purge, retention approval or route yet. Expired rows retain quota history and capacity fails closed until a reviewed purge exists. CI pending; no deployment.

Cloud fresh-install manifest now explicitly includes migration 012 and requires the community gate to remain disabled before commit. Install regression tests include rollback on an unexpectedly enabled community gate. CI pending.

## Candidate community claim envelope
Separate typed claim validator (not wired to any live transport): UUID claim,
owner, request key and fence, bounded idea, integer UTC epoch-second expiry
and lease. Lease must be live, at most 900 seconds remaining, and no later
than the expiry (at most 3600 seconds remaining). These are provisional
transport limits; local clock, identity mapping, durable receipt and SQL
claim/ack must independently enforce the contract. CI pending; no deployment.

## Cloud delivery candidate (013)
Owner-only SQL routines claim a single live transfer using a unique fence and a lease of at most 15 minutes. Expired claims are never automatically reissued. Exact acknowledgment is idempotent; revoked owners and stale unacknowledged leases are refused. Acknowledgment is a transport receipt, not review or execution. No runtime grants, local durable receipt, HTTP wiring, reconciliation or deployment. Manifest and installer counts updated; CI pending.

## Private durable receipt candidate (063)
Reuse existing operator-owned bridge identity mapping and local locked suggestion
admission, including shared feedback quotas. Exact cloud ID, key, owner, fence,
raw payload digest and lease bind the immutable receipt to a stored suggestion.
Local admission and receipt commit atomically; no task or inference created.
Receipt replay requires a live lease and current identity mapping. Cap 4096
receipts (provisional). Trusted operator connection only; no scoped bridge
runtime grant or network adapter, no cloud acknowledgment implementation.
Retention, local role audit and end-to-end reconciliation still required.
CI pending; no deployment.
