BEGIN;
-- Append-only administrator attestations. Never a bank connection or spend grant.
CREATE TABLE vault_reconciliation (
    sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    id uuid PRIMARY KEY,
    source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
    statement_at bigint NOT NULL CHECK(statement_at>0),
    recorded_at bigint NOT NULL CHECK(recorded_at>=statement_at),
    penny_entry_count bigint NOT NULL CHECK(penny_entry_count>=0),
    ledger_cash numeric(30,0) NOT NULL,
    observed_cash bigint NOT NULL CHECK(observed_cash BETWEEN 0 AND 1000000000000),
    evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
    evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
    evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
    reviewer_id uuid NOT NULL,
    policy_version text NOT NULL,
    coverage_confirmed boolean NOT NULL CHECK(coverage_confirmed)
);
CREATE TRIGGER vault_reconciliation_immutable BEFORE UPDATE OR DELETE
ON vault_reconciliation FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON vault_reconciliation FROM PUBLIC;
COMMIT;
