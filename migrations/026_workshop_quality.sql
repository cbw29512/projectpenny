BEGIN;
-- Review exact private artifact bytes, never authorize sale or publication.
CREATE TABLE workshop_quality_review (
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
 id uuid PRIMARY KEY,
 task_id uuid NOT NULL REFERENCES workshop_artifact(task_id),
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),
 usefulness boolean NOT NULL,
 accuracy boolean NOT NULL,
 originality boolean NOT NULL,
 privacy boolean NOT NULL,
 completeness boolean NOT NULL,
 revoked boolean NOT NULL,
 reviewer_id uuid NOT NULL,
 reviewed_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL,
 CHECK(NOT revoked OR NOT (usefulness OR accuracy OR originality OR privacy OR completeness))
);
CREATE INDEX workshop_quality_latest ON workshop_quality_review(task_id,sequence DESC);
CREATE TRIGGER workshop_quality_immutable BEFORE UPDATE OR DELETE ON workshop_quality_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_quality_review FROM PUBLIC;
COMMIT;
