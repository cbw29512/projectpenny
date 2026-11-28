BEGIN;
-- Independent human verdict for exact before/after content and reviewed brief.
-- This is evidence, never permission to publish, sell, or spend.
CREATE TABLE workshop_revision_review (
 task_id uuid PRIMARY KEY REFERENCES workshop_revision(task_id),
 parent_sha256 text NOT NULL CHECK(parent_sha256 ~ '^[a-f0-9]{64}$'),
 child_sha256 text NOT NULL CHECK(child_sha256 ~ '^[a-f0-9]{64}$'),
 basis_sha256 text NOT NULL CHECK(basis_sha256 ~ '^[a-f0-9]{64}$'),
 quality_review_id uuid NOT NULL REFERENCES workshop_quality_review(id),
 verdict text NOT NULL CHECK(verdict IN ('improved','not_improved')),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 reviewed_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TRIGGER workshop_revision_review_immutable BEFORE UPDATE OR DELETE ON workshop_revision_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_revision_review FROM PUBLIC;
COMMIT;
