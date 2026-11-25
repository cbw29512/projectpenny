# Scheduler core — first implementation slice
Objective: deterministic admission and next-task selection with no model calls or side effects.

## State
TaskSpec: immutable ID, requester ID (None for internal work), trusted tier (None for internal work), creation/expiry epoch seconds. Queue class is derived, never independently selected by a public caller.
QueueSnapshot: immutable active task, waiting tuple, paused state, last served member, measured rolling compute seconds per class.
Admission: a decision enum; this is not a reservation. Inputs must be authenticated and entitlement-resolved by the eventual adapter.

## Logic
1. Reject invalid, paused, expired or over-capacity proposals. Count active work toward per-member outstanding caps; waiting slots alone count toward class/global caps.
2. The selector returns no task while paused or active. Filter expired work. Choose oldest over-age work first; otherwise prefer another requester when available and pick the class with least consumed seconds relative to its target share. Within supporter class, higher tier wins; equal tiers use arrival order then ID.
3. Return only a candidate; the adapter must claim it transactionally and revalidate entitlement and policy before inference.
4. The adapter must expire queued records, track measured usage, implement atomic idempotency/quota, exclusive claims, fenced leases, cancellation, outcomes and notification outbox. No external effects are implemented in this slice.

Provisional: 900-second aging threshold; minimum 1 second charged per completed execution slice by future adapter; priority limited within class. Avoid immediate repeat of the same public member if another eligible task exists. This is not a latency guarantee. Runtime budgets and production authentication remain outstanding.

## Test
Run from repository root: `python -m unittest discover -s tests -v`.
Python 3.11+ standard library only. No credentials, models, database or network access.
