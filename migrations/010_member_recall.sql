BEGIN;
-- Bind explicit per-task permission to the consent epoch at submission.
CREATE TABLE member_recall_scope (
    task_id uuid PRIMARY KEY REFERENCES work_task(id),
    member_id uuid NOT NULL,
    epoch uuid NOT NULL
);
-- No preference text, no FK to deletable preference rows.
CREATE TABLE member_recall_snapshot (
    task_id uuid PRIMARY KEY REFERENCES member_recall_scope(task_id),
    fence uuid NOT NULL,
    preference_ids uuid[] NOT NULL CHECK (cardinality(preference_ids) BETWEEN 1 AND 3),
    recorded_at bigint NOT NULL
);
COMMIT;
