BEGIN;
-- Expiration is derived from original creation, including pre-migration drafts.
ALTER TABLE memory_candidate ADD COLUMN review_until timestamptz;
UPDATE memory_candidate SET review_until=created_at+interval '30 days';
ALTER TABLE memory_candidate ALTER COLUMN review_until SET NOT NULL;
ALTER TABLE memory_candidate ALTER COLUMN review_until SET DEFAULT (clock_timestamp()+interval '30 days');
ALTER TABLE memory_candidate ADD COLUMN purged_at timestamptz;

ALTER TABLE memory_maintenance_proposal ADD COLUMN review_until timestamptz;
UPDATE memory_maintenance_proposal SET review_until=to_timestamp(created_at)+interval '30 days';
ALTER TABLE memory_maintenance_proposal ALTER COLUMN review_until SET NOT NULL;
ALTER TABLE memory_maintenance_proposal ALTER COLUMN review_until SET DEFAULT (clock_timestamp()+interval '30 days');
ALTER TABLE memory_maintenance_proposal ADD COLUMN purged_at timestamptz;
CREATE INDEX memory_candidate_due ON memory_candidate(review_until,source_task_id) WHERE purged_at IS NULL;
CREATE INDEX memory_maintenance_due ON memory_maintenance_proposal(review_until,task_id) WHERE purged_at IS NULL;

-- Content-free audit for a logical redaction; not proof of physical erasure.
CREATE TABLE memory_draft_purge_event (
    task_id uuid PRIMARY KEY REFERENCES task_outcome(task_id),
    draft_kind text NOT NULL CHECK (draft_kind IN ('candidate','maintenance')),
    reviewer_id uuid NOT NULL,
    review_ref text NOT NULL CHECK (length(review_ref) BETWEEN 1 AND 128),
    purged_at bigint NOT NULL,
    policy_version text NOT NULL
);
COMMIT;
