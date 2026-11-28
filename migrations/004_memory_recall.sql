BEGIN;
-- Use PostgreSQL's built-in English text search. No embeddings or paid service.
CREATE INDEX business_memory_search ON business_memory
    USING gin (to_tsvector('english'::regconfig, content))
    WHERE revoked_at IS NULL;

-- Audit the selected source IDs, not their private text or the query text.
CREATE TABLE memory_recall_event (
    id uuid PRIMARY KEY,
    task_id uuid NOT NULL REFERENCES work_task(id),
    fence uuid NOT NULL,
    recorded_at bigint NOT NULL,
    policy_version text NOT NULL,
    rank_version text NOT NULL,
    selected_count integer NOT NULL CHECK (selected_count BETWEEN 0 AND 3)
);
CREATE INDEX memory_recall_event_task ON memory_recall_event(task_id);
CREATE TABLE memory_recall_source (
    event_id uuid NOT NULL REFERENCES memory_recall_event(id),
    source_task_id uuid NOT NULL REFERENCES business_memory(source_task_id),
    position integer NOT NULL CHECK (position BETWEEN 1 AND 3),
    PRIMARY KEY (event_id,position),
    UNIQUE (event_id,source_task_id)
);
COMMIT;
