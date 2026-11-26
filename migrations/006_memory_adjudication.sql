BEGIN;
-- A separate, single terminal decision; original proposal and source links remain intact.
CREATE TABLE memory_maintenance_decision (
    task_id uuid PRIMARY KEY REFERENCES memory_maintenance_proposal(task_id),
    verdict text NOT NULL CHECK (verdict IN ('applied','rejected','acknowledged')),
    reviewer_id uuid NOT NULL,
    review_ref text NOT NULL CHECK (length(review_ref) BETWEEN 1 AND 128),
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
    evidence_size integer NOT NULL CHECK (evidence_size BETWEEN 1 AND 16384),
    decided_at bigint NOT NULL,
    policy_version text NOT NULL,
    replacement_id uuid UNIQUE REFERENCES business_memory(source_task_id),
    CHECK (replacement_id IS NULL OR (verdict='applied' AND replacement_id=task_id))
);
COMMIT;
