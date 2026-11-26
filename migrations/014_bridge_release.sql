BEGIN;
-- A trusted reviewer approves the exact successful draft, not model intent.
CREATE TABLE bridge_release (
    question_id uuid PRIMARY KEY REFERENCES bridge_receipt(question_id),
    draft_sha256 text NOT NULL CHECK(draft_sha256 ~ '^[0-9a-f]{64}$'),
    reviewer_id uuid NOT NULL,
    identity_sha256 text NOT NULL CHECK(identity_sha256 ~ '^[0-9a-f]{64}$'),
    approved_at bigint NOT NULL,
    delivered_at bigint CHECK(delivered_at IS NULL OR delivered_at>=approved_at)
);
COMMIT;
