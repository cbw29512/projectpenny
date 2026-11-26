# Shared attempt budgets (private beta)
State: fixed global row per operation, two possible per-member rows (submit
and read) tied to provisioned member IDs. No untrusted key/cardinality or
per-window table growth. Separate role-restricted entrypoints. Not public.
Global row locks serialize read/check/increment. DB clock fixed minute and
UTC-day windows, not rolling; brief boundary bursts are possible. Local
scheduler/mailbox rolling admission quotas remain independent.
Provisional limits:
- submit: 6/member/minute; 40 total/minute; 600 total/UTC day.
- read: 12/member/minute; 120 total/minute; 3600 total/UTC day.
- claim: 6/minute; 1440/day (average at most one/minute if used all day).
- ack, answer, reject: each 12/minute; 360/day.
Only verified identities can reach this limiter in the HTTP core. Rejected
or malformed requests after allowance consume an attempt. Invalid tokens
are rejected earlier. Disabled/unknown members cannot create buckets.
The global bucket is checked before member increment, and denied member
requests do not consume global allowances. Separate member and bridge
operations prevent visitor traffic consuming bridge allowance. Accepted
attempts can still fail later. No automatic purchase of more capacity.
The adapter uses two independently scoped query connections, same as the
mailbox repository. Missing/invalid counter result or outage fails closed.
Migration 005 requires reapplying audited runtime grants. Existing live
deployment is not assumed. CI tests concurrent counters and actual roles.
Important limitation: this limits calls allowed beyond the shared counter,
not calls reaching Netlify or the counter database. Abusers can still
consume function/request/DB credits and create lock pressure. Provider-edge
controls, trusted ingress rate limiting, hard credit stop, connection and
statement deadlines, bounded body read time, actual usage measurement,
and adaptive client/worker backoff remain release gates. No claim of
unlimited traffic protection. No live provisioning or expenditure.
