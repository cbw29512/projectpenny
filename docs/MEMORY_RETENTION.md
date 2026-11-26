# Private memory draft retention
## Objective and state
Migration 007 adds a review deadline (provisional 30 days from creation) and
redaction timestamp to quarantined learning candidates and maintenance proposals.
Existing records derive deadlines from original creation. Approved memories
retain their independent existing expiration rules. Expired drafts cannot be
approved or adjudicated, even before cleanup. The administrator-only purge
event records task ID, kind, reviewer, reference, time and policy version.

## Flow
Authenticated internal administrator requests a bounded cleanup (max 25).
Guardian checks dedicated capability -> transaction under scheduler lock ->
select expired successful internal review drafts without approval or terminal
maintenance decision -> replace draft content, corresponding task payload and
outcome text with a constant marker -> append content-free purge audit.
Preserve task identity, source links and approved memory history. Repeat calls
skip redacted records. Audit failure rolls back all changes. Idempotency keys
remain reserved; replaying an original redacted payload will conflict.

## Limitations
Logical redaction only, not physical deletion. PostgreSQL MVCC/WAL, backups,
external evidence, other derived copies, malformed outputs without candidates,
decided proposals and approved histories require separate retention policy.
Separate explicit member preferences and consent repository are described in
[MEMBER_MEMORY.md](MEMBER_MEMORY.md); do not admit member data into business memory. No automatic cleanup scheduler, no public/admin HTTP
endpoint or database role isolation yet. The trusted admin adapter must
authenticate the reviewer; UUID alone is not authentication. No production
data was modified. Apply migrations 001–007 in order.
