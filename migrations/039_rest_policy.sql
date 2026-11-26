BEGIN;
-- Default disabled: upgrading code must never change live operations implicitly.
ALTER TABLE scheduler_control ADD COLUMN rest_enabled boolean NOT NULL DEFAULT false;
CREATE TABLE rest_policy_review (
 id uuid PRIMARY KEY,
 enabled boolean NOT NULL,
 policy_version text NOT NULL CHECK(policy_version='rest-concept-v1'),
 reviewed_at bigint NOT NULL,
 operator_uid bigint NOT NULL CHECK(operator_uid>=0)
);
CREATE TRIGGER rest_policy_review_immutable BEFORE UPDATE OR DELETE ON rest_policy_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON rest_policy_review FROM PUBLIC;
COMMIT;
