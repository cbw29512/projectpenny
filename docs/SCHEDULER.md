# Bounded attention contract v0.1
Approved direction: sequential, protected execution with verified supporter priority. Numerical settings are provisional pending benchmark.

## Defaults
- One active task and ten waiting slots: 3 free, 5 supporter, 2 business. No unbounded overflow or eviction for higher-paying members.
- Outstanding per member including active: free/Copper/Bronze 1, Silver/Gold 2, Platinum/Inner Circle 3. Proposed monthly tiers: free, $1, $3, $5, $10, $25, $50 respectively; pricing not approved and no live billing.
- Message limit 2000 characters plus independent body/token limits. Two safe transient retries at most, deadlines and bounded tool calls. Proposed chat slice 120s, business slice 15 min; benchmark first.
- Target rolling compute allocation: business 60%, supporters 30%, free 10%. Borrow idle capacity, age waiting work, prefer higher tiers within supporter class, avoid immediate repeat by same member when alternatives eligible.

## Logic flow
Admission: authenticate, validate, resolve verified entitlement, apply rate/quota limits. In a transaction lock scheduler control, dedupe requester/idempotency key, check caps, insert and charge quota once. If full, reject without inference or payment for that rejected task.
Dispatch: if not paused and no active task, choose eligible class by fairness/compute usage, then priority/age. Claim transactionally with fencing epoch. Recheck policy and entitlement. No incoming request preempts active work; admin/safety stop available.
Execute with finite deadline, tool/token/iteration budget. Validate output; atomically store final reply/outcome and release lock; durable outbox for notification. Long tasks checkpoint at safe boundaries with reserved capacity; otherwise pause explicitly. Failed tasks return honest status.
Recovery: reclaim expired leases only after safe worker isolation; reject stale results; reconcile external effects.
Availability: AVAILABLE, BUSY, FULL by admission class, PAUSED/DO_NOT_DISTURB. Derive from scheduler; cached non-LLM status. Opt-in bounded deduplicated availability subscriptions do not enqueue inference.

## Acceptance tests
Concurrent caps, duplicate submission, tier preference, no preemption, free/business fairness, per-user caps, spoofed/refunded entitlement, checkpoint bounds, fenced crash recovery, deadline exhaustion, notification dedupe, no model calls for busy/poll, no duplicated external effects. Use injected clock and model stub before live tests.
