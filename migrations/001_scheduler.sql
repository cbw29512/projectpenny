BEGIN;
CREATE TABLE scheduler_control (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    paused boolean NOT NULL DEFAULT false,
    last_member_id uuid
);
INSERT INTO scheduler_control DEFAULT VALUES;

-- Private administrative provisioning only; all writers use the control lock.
CREATE TABLE scheduler_entitlement (
    member_id uuid PRIMARY KEY,
    tier smallint NOT NULL CHECK (tier BETWEEN 1 AND 6),
    valid_until bigint NOT NULL
);

CREATE TABLE work_task (
    id uuid PRIMARY KEY,
    member_id uuid,
    tier_snapshot smallint,
    idempotency_key text NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 128),
    payload text NOT NULL CHECK (length(payload) BETWEEN 1 AND 2000),
    submitted_at bigint NOT NULL,
    deadline bigint NOT NULL CHECK (deadline > submitted_at),
    state text NOT NULL CHECK (state IN ('queued','running','succeeded','failed','expired','canceled')),
    fence uuid,
    started_at bigint,
    lease_until bigint,
    CHECK ((member_id IS NULL AND tier_snapshot IS NULL) OR
           (member_id IS NOT NULL AND tier_snapshot IS NOT NULL AND tier_snapshot BETWEEN 0 AND 6)),
    CHECK (state <> 'running' OR (fence IS NOT NULL AND started_at IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE UNIQUE INDEX one_running_task ON work_task ((1)) WHERE state = 'running';
CREATE UNIQUE INDEX member_request_key ON work_task (member_id, idempotency_key) WHERE member_id IS NOT NULL;
CREATE UNIQUE INDEX internal_request_key ON work_task (idempotency_key) WHERE member_id IS NULL;
CREATE INDEX live_tasks ON work_task (state, submitted_at) WHERE state IN ('queued','running');

CREATE TABLE task_outcome (
    task_id uuid PRIMARY KEY REFERENCES work_task(id),
    status text NOT NULL CHECK (status IN ('succeeded','failed','expired','canceled')),
    result text NOT NULL CHECK (length(result) <= 16000),
    finished_at bigint NOT NULL,
    compute_seconds integer NOT NULL CHECK (compute_seconds >= 0)
);
CREATE INDEX recent_outcomes ON task_outcome(finished_at);
COMMIT;
