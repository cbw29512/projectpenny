BEGIN;
-- One reviewed source draft can become at most one private opportunity.
CREATE TABLE business_draft_promotion (
 task_id uuid PRIMARY KEY REFERENCES business_draft_candidate(task_id),
 opportunity_id uuid NOT NULL UNIQUE REFERENCES business_opportunity(id),
 result_sha256 text NOT NULL CHECK(result_sha256 ~ '^[a-f0-9]{64}$'),
 reviewer_id uuid NOT NULL,
 reviewed_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TRIGGER business_draft_promotion_immutable BEFORE UPDATE OR DELETE ON business_draft_promotion
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON business_draft_promotion FROM PUBLIC;
COMMIT;
