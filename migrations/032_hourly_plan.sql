BEGIN;
-- One durable decision per UTC epoch hour; never a second scheduler.
CREATE TABLE hourly_plan (
    hour_slot bigint PRIMARY KEY CHECK(hour_slot>=0),
    recorded_at bigint NOT NULL CHECK(recorded_at/3600=hour_slot),
    outcome text NOT NULL CHECK(outcome IN ('scheduled','paused','blocked','busy','no_eligible_work','admission_refused')),
    opportunity_id uuid REFERENCES business_opportunity(id),
    task_id uuid UNIQUE REFERENCES workshop_task(task_id),
    CHECK ((outcome='scheduled')=(task_id IS NOT NULL)),
    CHECK (task_id IS NULL OR opportunity_id IS NOT NULL)
);
CREATE TRIGGER hourly_plan_immutable BEFORE UPDATE OR DELETE ON hourly_plan
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON hourly_plan FROM PUBLIC;
COMMIT;
