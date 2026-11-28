BEGIN;
-- A grant is approval of one exact watermarked private edition, not a sale.
CREATE TABLE workshop_beta_grant (
 id uuid PRIMARY KEY,
 preview_id uuid NOT NULL REFERENCES workshop_preview(id),
 member_id uuid NOT NULL,
 quality_review_id uuid NOT NULL REFERENCES workshop_quality_review(id),
 brand_version text NOT NULL REFERENCES product_brand_asset(version),
 edition_sha256 text NOT NULL CHECK(edition_sha256 ~ '^[a-f0-9]{64}$'),
 variant_sha256 text NOT NULL CHECK(variant_sha256 ~ '^[a-f0-9]{64}$'),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 granted_at bigint NOT NULL,
 expires_at bigint NOT NULL CHECK(expires_at>granted_at AND expires_at<=granted_at+604800),
 policy_version text NOT NULL,
 UNIQUE(preview_id,member_id)
);
CREATE TABLE workshop_beta_revocation (
 grant_id uuid PRIMARY KEY REFERENCES workshop_beta_grant(id),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 revoked_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TRIGGER workshop_beta_grant_immutable BEFORE UPDATE OR DELETE ON workshop_beta_grant
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER workshop_beta_revocation_immutable BEFORE UPDATE OR DELETE ON workshop_beta_revocation
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_beta_grant,workshop_beta_revocation FROM PUBLIC;
COMMIT;
