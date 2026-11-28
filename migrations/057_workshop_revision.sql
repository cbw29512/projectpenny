BEGIN;
-- One reviewed revision request per preview. No member identifiers, feedback
-- bodies or individual rating values. Existing Workshop admission owns quotas.
CREATE TABLE workshop_revision (
 task_id uuid PRIMARY KEY REFERENCES workshop_task(task_id),
 parent_task_id uuid NOT NULL REFERENCES workshop_artifact(task_id),
 preview_id uuid NOT NULL UNIQUE REFERENCES workshop_preview(id),
 parent_sha256 text NOT NULL CHECK(parent_sha256 ~ '^[a-f0-9]{64}$'),
 basis_sha256 text NOT NULL CHECK(basis_sha256 ~ '^[a-f0-9]{64}$'),
 brief_sha256 text NOT NULL CHECK(brief_sha256 ~ '^[a-f0-9]{64}$'),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 requested_at bigint NOT NULL,
 policy_version text NOT NULL,
 CHECK(task_id<>parent_task_id)
);
CREATE TRIGGER workshop_revision_immutable BEFORE UPDATE OR DELETE ON workshop_revision
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_revision FROM PUBLIC;
COMMIT;
