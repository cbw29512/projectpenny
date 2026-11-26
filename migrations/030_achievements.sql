BEGIN;
-- Immutable disclosure reviews, not an automatic award or payment authority.
CREATE TABLE achievement_review (
 sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 id uuid NOT NULL UNIQUE,
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 code text NOT NULL CHECK(code IN ('first_dollar','in_the_green','proof_of_concept')),
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
 approved boolean NOT NULL,
 reviewer_id uuid NOT NULL,
 reviewed_at bigint NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL
);
CREATE INDEX achievement_review_latest ON achievement_review(code,sequence DESC);
CREATE TRIGGER achievement_review_immutable BEFORE UPDATE OR DELETE ON achievement_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON achievement_review FROM PUBLIC;
COMMIT;
