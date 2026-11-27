BEGIN;
CREATE TABLE workshop_progress_snapshot (
 sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id uuid NOT NULL UNIQUE,
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 product_id uuid NOT NULL REFERENCES business_product(id),
 preview_id uuid REFERENCES workshop_preview(id),
 stage text NOT NULL CHECK(stage IN ('prototype_reviewed','preview_reviewed','revision_reviewed','review_withdrawn')),
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
 generated_at bigint NOT NULL,
 expires_at bigint NOT NULL CHECK(expires_at>generated_at AND expires_at-generated_at<=3600),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL,
 CHECK((stage='preview_reviewed' AND preview_id IS NOT NULL)
 OR (stage IN ('prototype_reviewed','revision_reviewed') AND preview_id IS NULL)
 OR stage='review_withdrawn')
);
CREATE TRIGGER workshop_progress_immutable BEFORE UPDATE OR DELETE ON workshop_progress_snapshot
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_progress_snapshot FROM PUBLIC;
COMMIT;
