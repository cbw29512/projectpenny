BEGIN;
-- Exact Maker-reviewed beta preview, not a catalog entry or sale.
CREATE TABLE workshop_preview (
 id uuid PRIMARY KEY,
 task_id uuid NOT NULL REFERENCES workshop_artifact(task_id),
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 artifact_sha256 text NOT NULL CHECK(artifact_sha256 ~ '^[a-f0-9]{64}$'),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
 preview_text text NOT NULL CHECK(length(preview_text) BETWEEN 1 AND 2000),
 preview_sha256 text NOT NULL CHECK(preview_sha256 ~ '^[a-f0-9]{64}$'),
 reviewer_id uuid NOT NULL,
 reviewed_at bigint NOT NULL,
 expires_at bigint NOT NULL CHECK(expires_at>reviewed_at AND expires_at<=reviewed_at+604800),
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE TABLE workshop_preview_withdrawal (
 preview_id uuid PRIMARY KEY REFERENCES workshop_preview(id),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE INDEX workshop_preview_task ON workshop_preview(task_id);
CREATE TRIGGER workshop_preview_immutable BEFORE UPDATE OR DELETE ON workshop_preview
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER workshop_preview_withdrawal_immutable BEFORE UPDATE OR DELETE ON workshop_preview_withdrawal
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_preview,workshop_preview_withdrawal FROM PUBLIC;
COMMIT;
