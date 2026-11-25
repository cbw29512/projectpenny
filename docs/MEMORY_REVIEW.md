# Evidence review and private business recall

## Definition of done
A trusted administrator adapter can explicitly approve the exact quarantined
candidate using independently reviewed evidence, a reviewer identity, an
external review reference and a bounded retention window. A separate read-only
interface returns only reviewed, unrevoked, unexpired business memories to a
currently fenced internal task. Revocation excludes records from later reads.

## State
Migration 003 stores an approved snapshot, source candidate FK, evidence
fingerprint and byte count, reviewer UUID, review reference, approval and
expiration instants (UTC epoch seconds), optional revocation. Approval/revocation
events are inserted atomically with state changes; no application update/delete
of events. One approval per source; no reactivation. Corrections require a new
candidate. Existing quarantine remains unchanged. Evidence bytes are not copied;
the authenticated reviewer must preserve evidence and map the reference to it.
A hash is not proof of factual accuracy or provenance authenticity.

## Logic
Independent reviewer assesses evidence and exact candidate -> trusted adapter
authenticates reviewer -> Guardian explicit approve permission -> transaction
checks source outcome and exact candidate content -> approved snapshot + event.
A later revocation inserts a separate event. Recall requires live internal task
ID and fence, unpaused scheduler and Guardian permission; at most 3 complete
records and 1500 content characters. No member task can use this recall path.

## Boundaries and limitations
Apply migrations 001–003 in order. These Python entry points are internal, not
authenticated HTTP endpoints. The caller must be an authenticated, isolated
administrator adapter; UUID arguments alone are not authentication. The model
has no adapter or DB credentials. Production role separation and append-only
DB permissions are still required. Reviewed content remains data, never policy
or authority. No automatic prompt injection of recall yet; in-flight recall
snapshots cannot be revoked retroactively. Retention expires recall, not storage;
physical deletion and consent are still pending. No member records or unattended
self-approval. Initial retention maximum 365 days and recall limits are
provisional. No extra paid service or deployment.
