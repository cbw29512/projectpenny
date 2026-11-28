BEGIN;
-- One proposal per successful internal review outcome. This is not trusted memory.
CREATE TABLE memory_candidate (
    source_task_id uuid PRIMARY KEY REFERENCES task_outcome(task_id),
    scope text NOT NULL DEFAULT 'private_business' CHECK (scope = 'private_business'),
    kind text NOT NULL CHECK (kind IN ('lesson','failure','idea','skill','milestone')),
    content text NOT NULL CHECK (length(content) BETWEEN 1 AND 1000),
    validation_state text NOT NULL DEFAULT 'quarantined' CHECK (validation_state = 'quarantined'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
COMMIT;
