# Durable private bridge receipts
Local migration 013: operator-provisioned one-to-one cloud-to-local member
mapping, disabled by removing enabled flag; unique question/fence/task
receipt, exact payload hash, deadline and confirmed ack timestamp.
No automatic local account creation or imported tier/memory consent.
Admission validates lease and identity, acquires the existing scheduler
transaction lock, validates mapping, checks exact replay, then invokes
the shared admission primitive with a reserved bridge key and shortened
deadline. Task and receipt commit together. No second task on replay.
Regular member/internal submissions cannot use reserved bridge: prefix.
Receipts are capped at 4096; fail closed at capacity. Retention and durable
tombstones still required; no deletion/reset of replay or quota protection.
The scheduler can process a local draft before remote ack succeeds; draft
is not public delivery. Trusted caller records ack only after remote
confirmation. Ack is fenced and idempotent; expired or disabled mapping
cannot acknowledge. Future release and outbox must recheck current mapping,
identity, acknowledgement, expiry and separately authorized content.
This is not a running bridge, authenticated operator service, or automated
publication. No local credentials or records in Git. No deployment/spend.
