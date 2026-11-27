BEGIN;
-- First slice: structured, private feedback only. No free-form comments,
-- private asset access, inference, recognition or commercial authority.
CREATE TABLE workshop_feedback (
    id uuid PRIMARY KEY,
    preview_id uuid NOT NULL REFERENCES workshop_preview(id),
    preview_sha256 text NOT NULL CHECK(preview_sha256 ~ '^[a-f0-9]{64}$'),
    member_id uuid NOT NULL,
    request_key text NOT NULL CHECK(request_key ~ '^[A-Za-z0-9_-]{1,80}$'),
    usefulness smallint CHECK(usefulness BETWEEN 1 AND 5),
    purchase_interest text CHECK(purchase_interest IN ('yes','maybe','no')),
    submitted_at bigint NOT NULL,
    withdrawn_at bigint CHECK(withdrawn_at>=submitted_at),
    policy_version text NOT NULL,
    UNIQUE(member_id,request_key),
    UNIQUE(member_id,preview_id),
    CHECK((withdrawn_at IS NULL AND usefulness IS NOT NULL AND purchase_interest IS NOT NULL)
       OR (withdrawn_at IS NOT NULL AND usefulness IS NULL AND purchase_interest IS NULL))
);
CREATE INDEX workshop_feedback_time ON workshop_feedback(submitted_at);
CREATE INDEX workshop_feedback_owner_time ON workshop_feedback(member_id,submitted_at);
CREATE INDEX workshop_feedback_preview ON workshop_feedback(preview_id);
REVOKE ALL ON workshop_feedback FROM PUBLIC;
COMMIT;
