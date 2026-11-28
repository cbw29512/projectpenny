BEGIN;
-- Private printable checklist prototypes; never a publication or sale.
CREATE TABLE workshop_task (
 task_id uuid PRIMARY KEY REFERENCES work_task(id),
 opportunity_id uuid NOT NULL REFERENCES business_opportunity(id),
 requested_by uuid NOT NULL,
 policy_version text NOT NULL
);
CREATE INDEX workshop_opportunity ON workshop_task(opportunity_id);
CREATE TABLE workshop_artifact (
 task_id uuid PRIMARY KEY REFERENCES workshop_task(task_id),
 format_version text NOT NULL CHECK(format_version='checklist-text-v1'),
 content text NOT NULL CHECK(length(content) BETWEEN 1 AND 6000),
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[a-f0-9]{64}$'),
 result_sha256 text NOT NULL CHECK(result_sha256 ~ '^[a-f0-9]{64}$'),
 created_at bigint NOT NULL
);
CREATE TRIGGER workshop_task_immutable BEFORE UPDATE OR DELETE ON workshop_task
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER workshop_artifact_immutable BEFORE UPDATE OR DELETE ON workshop_artifact
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_task,workshop_artifact FROM PUBLIC;
COMMIT;
