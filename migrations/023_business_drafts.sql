BEGIN;
-- Explicit internal admission record; a prefix alone is not provenance.
CREATE TABLE business_draft_task (
 task_id uuid PRIMARY KEY REFERENCES work_task(id),
 requested_by uuid NOT NULL,
 policy_version text NOT NULL
);
CREATE TABLE business_draft_candidate (
 task_id uuid PRIMARY KEY REFERENCES business_draft_task(task_id),
 category text NOT NULL CHECK(category IN ('digital_product','content','software_utility','service_research')),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
 hypothesis text NOT NULL CHECK(length(hypothesis) BETWEEN 1 AND 1000),
 metric text NOT NULL CHECK(metric IN ('qualified_interest','prototype_checks_passed','validated_requirements')),
 target integer NOT NULL CHECK(target BETWEEN 1 AND 10000),
 duration_seconds integer NOT NULL CHECK(duration_seconds BETWEEN 60 AND 604800),
 additional_cash_cents bigint NOT NULL CHECK(additional_cash_cents=0),
 result_sha256 text NOT NULL CHECK(result_sha256 ~ '^[a-f0-9]{64}$')
);
CREATE TRIGGER business_draft_task_immutable BEFORE UPDATE OR DELETE ON business_draft_task
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER business_draft_candidate_immutable BEFORE UPDATE OR DELETE ON business_draft_candidate
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON business_draft_task,business_draft_candidate FROM PUBLIC;
COMMIT;
