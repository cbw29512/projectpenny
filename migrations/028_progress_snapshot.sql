BEGIN;
-- Reviewed, immutable candidate for a cached public read model.
CREATE TABLE progress_snapshot (
 version bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id uuid NOT NULL UNIQUE,
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
 payload_sha256 text NOT NULL CHECK(payload_sha256 ~ '^[a-f0-9]{64}$'),
 generated_at bigint NOT NULL,
 expires_at bigint NOT NULL CHECK(expires_at>generated_at AND expires_at-generated_at<=3600),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE TRIGGER progress_snapshot_immutable BEFORE UPDATE OR DELETE ON progress_snapshot
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON progress_snapshot FROM PUBLIC;
COMMIT;
