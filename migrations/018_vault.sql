BEGIN;
-- Narrow USD journal: each typed event maps to an immutable pair of accounts.
-- Integer cents avoid rounding errors. No bank integration or spending authority.
CREATE TABLE vault_entry (
    id uuid PRIMARY KEY,
    source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
    kind text NOT NULL CHECK(kind IN ('commercial_receipt','commercial_refund',
        'community_support','founder_funding','operating_expense','payment_fee',
        'founder_paid_expense','founder_income','founder_expense')),
    cents bigint NOT NULL CHECK(cents BETWEEN 1 AND 1000000000000),
    occurred_at bigint NOT NULL CHECK(occurred_at>0),
    recorded_at bigint NOT NULL CHECK(recorded_at>=occurred_at),
    evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
    evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[0-9a-f]{64}$'),
    evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
    reviewer_id uuid NOT NULL,
    policy_version text NOT NULL,
    reversal_of uuid UNIQUE,
    UNIQUE(id,kind,cents),
    FOREIGN KEY(reversal_of,kind,cents) REFERENCES vault_entry(id,kind,cents),
    CHECK(reversal_of IS NULL OR reversal_of<>id)
);
CREATE FUNCTION vault_append_only() RETURNS trigger LANGUAGE plpgsql AS $immutable$
BEGIN
    RAISE EXCEPTION 'vault entries are append-only';
END;
$immutable$;
CREATE TRIGGER vault_immutable BEFORE UPDATE OR DELETE ON vault_entry
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE FUNCTION vault_check_reversal() RETURNS trigger LANGUAGE plpgsql AS $reverse$
BEGIN
    IF NEW.reversal_of IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM vault_entry WHERE id=NEW.reversal_of AND reversal_of IS NULL
          AND occurred_at<=NEW.occurred_at
    ) THEN RAISE EXCEPTION 'invalid reversal'; END IF;
    RETURN NEW;
END;
$reverse$;
CREATE TRIGGER vault_reversal BEFORE INSERT ON vault_entry
FOR EACH ROW EXECUTE FUNCTION vault_check_reversal();
-- Each entry produces exactly two balanced postings; no arbitrary transfer API.
CREATE VIEW vault_posting AS
WITH pairs AS (
    SELECT id,kind,cents,reversal_of,
      CASE kind
        WHEN 'commercial_receipt' THEN 'penny.cash'
        WHEN 'commercial_refund' THEN 'penny.refunds'
        WHEN 'community_support' THEN 'penny.cash'
        WHEN 'founder_funding' THEN 'penny.cash'
        WHEN 'operating_expense' THEN 'penny.expense'
        WHEN 'payment_fee' THEN 'penny.fees'
        WHEN 'founder_paid_expense' THEN 'penny.expense'
        WHEN 'founder_income' THEN 'founder.cash'
        WHEN 'founder_expense' THEN 'founder.expense'
      END AS debit,
      CASE kind
        WHEN 'commercial_receipt' THEN 'penny.commercial'
        WHEN 'commercial_refund' THEN 'penny.cash'
        WHEN 'community_support' THEN 'penny.support'
        WHEN 'founder_funding' THEN 'penny.contributed'
        WHEN 'operating_expense' THEN 'penny.cash'
        WHEN 'payment_fee' THEN 'penny.cash'
        WHEN 'founder_paid_expense' THEN 'penny.contributed'
        WHEN 'founder_income' THEN 'founder.income'
        WHEN 'founder_expense' THEN 'founder.cash'
      END AS credit
    FROM vault_entry
)
SELECT id AS entry_id,debit AS account,
       CASE WHEN reversal_of IS NULL THEN cents ELSE -cents END AS debit_minor
FROM pairs
UNION ALL
SELECT id,credit,CASE WHEN reversal_of IS NULL THEN -cents ELSE cents END
FROM pairs;
REVOKE ALL ON vault_entry,vault_posting FROM PUBLIC;
COMMIT;
