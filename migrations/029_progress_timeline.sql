BEGIN;
-- One disclosure review per immutable terminal experiment event.
CREATE TABLE progress_timeline_event (
 sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id uuid NOT NULL UNIQUE,
 experiment_event_id uuid NOT NULL UNIQUE REFERENCES business_experiment_event(id),
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 kind text NOT NULL CHECK(kind IN ('target_met','target_missed','experiment_stopped','experiment_rejected')),
 occurred_at bigint NOT NULL CHECK(occurred_at>0),
 recorded_at bigint NOT NULL CHECK(recorded_at>=occurred_at),
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
-- Suppression never erases history or exposes a private reason.
CREATE TABLE progress_timeline_suppression (
 event_id uuid PRIMARY KEY REFERENCES progress_timeline_event(id),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE INDEX progress_timeline_order ON progress_timeline_event(occurred_at DESC,sequence DESC);
CREATE TRIGGER progress_timeline_immutable BEFORE UPDATE OR DELETE ON progress_timeline_event
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER progress_timeline_suppression_immutable BEFORE UPDATE OR DELETE ON progress_timeline_suppression
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON progress_timeline_event,progress_timeline_suppression FROM PUBLIC;
COMMIT;
