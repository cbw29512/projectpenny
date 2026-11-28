BEGIN;
-- Proposals only; no mutation of approved memories or audit history.
CREATE TABLE memory_maintenance_proposal (
    task_id uuid PRIMARY KEY REFERENCES task_outcome(task_id),
    action text NOT NULL CHECK (action IN ('correct','consolidate','outdated','contradiction')),
    rationale text NOT NULL CHECK (length(rationale) BETWEEN 1 AND 500),
    replacement text CHECK (length(replacement) BETWEEN 1 AND 1000),
    state text NOT NULL DEFAULT 'quarantined' CHECK (state = 'quarantined'),
    created_at bigint NOT NULL,
    policy_version text NOT NULL,
    CHECK ((action IN ('correct','consolidate') AND replacement IS NOT NULL)
        OR (action IN ('outdated','contradiction') AND replacement IS NULL))
);
CREATE TABLE memory_maintenance_source (
    task_id uuid NOT NULL REFERENCES memory_maintenance_proposal(task_id),
    source_task_id uuid NOT NULL REFERENCES business_memory(source_task_id),
    PRIMARY KEY (task_id,source_task_id)
);
COMMIT;
