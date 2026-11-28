BEGIN;
-- Private catalog candidate, not a storefront, price offer or authorization.
CREATE TABLE business_product (
 id uuid PRIMARY KEY,
 task_id uuid NOT NULL UNIQUE REFERENCES workshop_artifact(task_id),
 quality_review_id uuid NOT NULL REFERENCES workshop_quality_review(id),
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
 reviewer_id uuid NOT NULL,
 created_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE TABLE business_product_withdrawal (
 product_id uuid PRIMARY KEY REFERENCES business_product(id),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
-- One original journal entry belongs to at most one product. Reversals
-- inherit attribution from the original, rather than adding another link.
CREATE TABLE business_product_finance (
 entry_id uuid PRIMARY KEY REFERENCES vault_entry(id),
 product_id uuid NOT NULL REFERENCES business_product(id),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE INDEX business_product_finance_product ON business_product_finance(product_id);
CREATE TRIGGER business_product_immutable BEFORE UPDATE OR DELETE ON business_product
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER business_product_withdrawal_immutable BEFORE UPDATE OR DELETE ON business_product_withdrawal
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER business_product_finance_immutable BEFORE UPDATE OR DELETE ON business_product_finance
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON business_product,business_product_withdrawal,business_product_finance FROM PUBLIC;
COMMIT;
