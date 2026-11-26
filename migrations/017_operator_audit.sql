BEGIN;
CREATE TABLE runtime_operator_event (
    id uuid PRIMARY KEY,
    action text NOT NULL CHECK(action IN ('stop','start_inference','start_bridge','recover_inference','clear_bridge_block')),
    recorded_at bigint NOT NULL,
    operator_uid bigint NOT NULL CHECK(operator_uid>=0),
    task_id uuid REFERENCES work_task(id)
);
COMMIT;
