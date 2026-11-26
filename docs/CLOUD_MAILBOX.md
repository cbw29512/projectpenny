# Cloud mailbox SQL core (private beta foundation)
State/schema first: separately provisioned managed PostgreSQL; do not apply
cloud migrations to local Penny. Default closed singleton gate, provisioned
member allowlist, question owner + UUID idempotency key, body, expiration,
state, claim fence, local task ID and bounded answer. One outstanding per
member; at most eight total outstanding, one bridge transfer, 512 retained
rows. Rolling 3/hour,10/day per member and 20/hour,120/day aggregate.
All members use free-beta limits; no cloud tier assertions. No new spend.

Logic: trusted server resolves verified member -> mailbox_submit transaction
-> bridge claims under same singleton lock -> local durable admission ->
ack -> approved answer. No automatic claim reissue; expire uncertain transfer
rather than risk duplicate execution. Idempotent ack and identical answer
retry, mismatched fence rejected. Private owner read, no public reply. Terminal
rows kept 48h to preserve rolling quotas, then batch purge (50 rows). Purge
must be explicitly scheduled later; full database closes admission, not
unbounded growth. Disable member prevents new admission, reads and answers.
Pause prevents new questions/claims, allows in-flight completion.
 
Implementation: netlify/mailbox/001–003 SQL, tested against disposable
PostgreSQL in CI. SQL routines use invoker privileges and revoke PUBLIC
execution. They are NOT deployed routes, a complete authorization system, or
a replacement for Netlify edge protection. Production must use a dedicated
schema, fixed search path, scoped server roles with no direct DML where
possible, audited role grants, authenticated member mapping and bridge
credentials, TLS, bounded HTTP body/request/read rates and DB timeouts.
Do not expose raw SQL functions or let callers supply owner identity.
No Netlify package, project, database or credentials configured. No live
polling or costs. Actual Netlify runtime integration and compatibility,
account quotas, private local mapping, outbox and recovery reconciliation,
full retention, and independent response release review remain pending.
Tests use synthetic evidence; no real members. No DDoS immunity claims.
