BEGIN;
CREATE TABLE community_suggestion (
 id uuid PRIMARY KEY,
 member_id uuid NOT NULL,
 request_key text NOT NULL CHECK(request_key ~ '^[A-Za-z0-9_-]{1,80}$'),
 body text NOT NULL CHECK(length(body) BETWEEN 1 AND 500),
 body_sha256 text NOT NULL CHECK(body_sha256 ~ '^[a-f0-9]{64}$'),
 duplicate_sha256 text NOT NULL CHECK(duplicate_sha256 ~ '^[a-f0-9]{64}$'),
 submitted_at bigint NOT NULL,
 policy_version text NOT NULL,
 UNIQUE(member_id,request_key),
 UNIQUE(member_id,duplicate_sha256)
);
CREATE INDEX community_suggestion_time ON community_suggestion(submitted_at);
CREATE INDEX community_suggestion_owner_time ON community_suggestion(member_id,submitted_at);
CREATE TABLE community_suggestion_review (
 suggestion_id uuid PRIMARY KEY REFERENCES community_suggestion(id),
 body_sha256 text NOT NULL CHECK(body_sha256 ~ '^[a-f0-9]{64}$'),
 verdict text NOT NULL CHECK(verdict IN ('eligible','rejected','deferred')),
 reason text NOT NULL CHECK(reason IN ('mission_fit','off_topic','unsafe','spam','not_feasible','needs_research')),
 reviewer_id uuid NOT NULL,
 reviewed_at bigint NOT NULL,
 policy_version text NOT NULL,
 CHECK((verdict='eligible' AND reason='mission_fit')
 OR (verdict='rejected' AND reason IN ('off_topic','unsafe','spam'))
 OR (verdict='deferred' AND reason IN ('not_feasible','needs_research')))
);
CREATE TRIGGER community_suggestion_immutable BEFORE UPDATE OR DELETE ON community_suggestion
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER community_suggestion_review_immutable BEFORE UPDATE OR DELETE ON community_suggestion_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON community_suggestion,community_suggestion_review FROM PUBLIC;
COMMIT;
