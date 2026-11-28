BEGIN;
-- Planning ceiling only. No budget row means zero; no payment authorization.
CREATE TABLE vault_budget_review (
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
 id uuid PRIMARY KEY,
 reconciliation_id uuid NOT NULL REFERENCES vault_reconciliation(id),
 ceiling_cents bigint NOT NULL CHECK(ceiling_cents BETWEEN 0 AND 1000000000000),
 obligations_cents bigint NOT NULL CHECK(obligations_cents BETWEEN 0 AND 1000000000000),
 reserve_cents bigint NOT NULL CHECK(reserve_cents BETWEEN 0 AND 1000000000000),
 reviewed_at bigint NOT NULL,
 expires_at bigint NOT NULL CHECK(expires_at>reviewed_at AND expires_at-reviewed_at<=86400),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE TABLE vault_reservation (
 request_id uuid PRIMARY KEY REFERENCES vault_spend_request(id),
 budget_id uuid NOT NULL REFERENCES vault_budget_review(id),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 policy_version text NOT NULL
);
-- Never silently release a hold because a quote or policy expired.
CREATE TABLE vault_reservation_release (
 request_id uuid PRIMARY KEY REFERENCES vault_reservation(request_id),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE TRIGGER vault_budget_immutable BEFORE UPDATE OR DELETE ON vault_budget_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER vault_reservation_immutable BEFORE UPDATE OR DELETE ON vault_reservation
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER vault_reservation_release_immutable BEFORE UPDATE OR DELETE ON vault_reservation_release
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON vault_budget_review,vault_reservation,vault_reservation_release FROM PUBLIC;
COMMIT;
