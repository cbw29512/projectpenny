BEGIN;
-- Approved canonical artwork identity; private metadata, never publication authority.
CREATE TABLE product_brand_asset (
 version text PRIMARY KEY CHECK(version ~ '^[A-Za-z0-9_.-]{1,64}$'),
 artwork_sha256 text NOT NULL CHECK(artwork_sha256 ~ '^[a-f0-9]{64}$'),
 artwork_size integer NOT NULL CHECK(artwork_size BETWEEN 1 AND 2097152),
 approved_name text NOT NULL CHECK(approved_name='Penny'),
 reviewer_id uuid NOT NULL,
 rights_ref text NOT NULL CHECK(rights_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 approved_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TABLE product_brand_revocation (
 version text PRIMARY KEY REFERENCES product_brand_asset(version),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 revoked_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TRIGGER product_brand_asset_immutable BEFORE UPDATE OR DELETE ON product_brand_asset
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER product_brand_revocation_immutable BEFORE UPDATE OR DELETE ON product_brand_revocation
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON product_brand_asset,product_brand_revocation FROM PUBLIC;
COMMIT;
