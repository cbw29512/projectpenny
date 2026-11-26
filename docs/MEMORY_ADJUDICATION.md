# Administrator memory adjudication
## Objective and state
Migration 006 records a single terminal decision linked to the original
maintenance proposal, reviewer, independent evidence fingerprint, timestamp,
policy version and optional replacement memory. The proposal remains immutable
quarantined history; its decision row is the authoritative disposition.

## Logic
Trusted authenticated administrator reviews the exact proposal and evidence.
Separate Guardian capability -> strict expected proposal parser -> transaction
under existing scheduler lock -> verify exact action, rationale, replacement
and source set, successful internal task, and no prior decision.
Apply correction/consolidation only if every source is still active and all
source kinds match. Insert a new candidate and approved memory linked to the
maintenance task, record approval and retire originals with revocation events.
Replacement retention cannot exceed any original expiry. Outdated application
retires one source without replacement. Contradiction can be acknowledged but
not applied; explicit corrective evidence and a new proposal are required.
Rejection/acknowledgment record disposition only. All effects and terminal
decision commit atomically; replay or stale sources cannot change state.

## Limits
No model access to this interface. Caller authentication and isolated DB roles
are not implemented here; reviewer UUID alone is not authentication. Fingerprint
establishes integrity, not truth. Old text remains stored for audit until a
separate retention/deletion process is implemented. Review references must
point to independently preserved evidence. Existing in-flight inference
snapshots cannot be retracted. No unattended approval or deployment.
