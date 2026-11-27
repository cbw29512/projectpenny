BEGIN;
-- Terminal review binds the exact feedback row and preview version.
-- Do not duplicate rating or purchase-interest values into permanent audit.
CREATE TABLE workshop_feedback_review (
    feedback_id uuid PRIMARY KEY REFERENCES workshop_feedback(id),
    preview_sha256 text NOT NULL CHECK(preview_sha256 ~ '^[a-f0-9]{64}$'),
    verdict text NOT NULL CHECK(verdict IN ('eligible','rejected')),
    reason text NOT NULL CHECK(reason IN ('valid_feedback','spam','abuse','integrity')),
    reviewer_id uuid NOT NULL,
    reviewed_at bigint NOT NULL,
    policy_version text NOT NULL,
    CHECK((verdict='eligible' AND reason='valid_feedback')
       OR (verdict='rejected' AND reason IN ('spam','abuse','integrity')))
);
CREATE TRIGGER workshop_feedback_review_immutable
    BEFORE UPDATE OR DELETE ON workshop_feedback_review
    FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_feedback_review FROM PUBLIC;
COMMIT;
