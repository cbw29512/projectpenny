BEGIN;
-- A reviewed snapshot, distinct from quarantined model output.
CREATE TABLE business_memory (
    source_task_id uuid PRIMARY KEY REFERENCES memory_candidate(source_task_id),
    kind text NOT NULL CHECK (kind IN ('lesson','failure','idea','skill','milestone')),
    content text NOT NULL CHECK (length(content) BETWEEN 1 AND 1000),
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
    evidence_size integer NOT NULL CHECK (evidence_size BETWEEN 1 AND 16384),
    review_ref text NOT NULL CHECK (length(review_ref) BETWEEN 1 AND 128),
    reviewed_by uuid NOT NULL,
    approved_at bigint NOT NULL,
    expires_at bigint NOT NULL CHECK (expires_at > approved_at),
    revoked_at bigint CHECK (revoked_at >= approved_at)
);
CREATE INDEX business_memory_recall ON business_memory(approved_at DESC, source_task_id)
    WHERE revoked_at IS NULL;
CREATE TABLE business_memory_event (
    source_task_id uuid NOT NULL REFERENCES business_memory(source_task_id),
    action text NOT NULL CHECK (action IN ('approved','revoked')),
    actor_id uuid NOT NULL,
    review_ref text NOT NULL CHECK (length(review_ref) BETWEEN 1 AND 128),
    recorded_at bigint NOT NULL,
    policy_version text NOT NULL,
    PRIMARY KEY (source_task_id, action)
);
COMMIT;
