BEGIN;
-- Requests are nonbinding drafts. No approval or payment authority in this migration.
CREATE TABLE vault_spend_request (
 id uuid PRIMARY KEY,
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 purpose text NOT NULL CHECK(purpose IN ('compute','hosting','software','business_supplies')),
 cents bigint NOT NULL CHECK(cents BETWEEN 1 AND 1000000000000),
 quote_ref text NOT NULL CHECK(quote_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 reviewer_id uuid NOT NULL,
 created_at bigint NOT NULL,
 expires_at bigint NOT NULL CHECK(expires_at>created_at AND expires_at-created_at<=604800),
 policy_version text NOT NULL
);
CREATE TABLE vault_spend_rejection (
 request_id uuid PRIMARY KEY REFERENCES vault_spend_request(id),
 reviewer_id uuid NOT NULL,
 reason text NOT NULL CHECK(reason IN ('cost','risk','insufficient_evidence','not_needed','policy')),
 recorded_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TRIGGER vault_spend_request_immutable BEFORE UPDATE OR DELETE ON vault_spend_request
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER vault_spend_rejection_immutable BEFORE UPDATE OR DELETE ON vault_spend_rejection
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON vault_spend_request,vault_spend_rejection FROM PUBLIC;
COMMIT;
