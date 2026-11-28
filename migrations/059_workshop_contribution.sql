BEGIN;
-- Trusted admission links exact reviewed suggestions, never their body or owner.
CREATE TABLE workshop_revision_suggestion (
 task_id uuid NOT NULL REFERENCES workshop_revision(task_id),
 suggestion_id uuid NOT NULL REFERENCES community_suggestion(id),
 body_sha256 text NOT NULL CHECK(body_sha256 ~ '^[a-f0-9]{64}$'),
 PRIMARY KEY(task_id,suggestion_id)
);
CREATE TRIGGER workshop_revision_suggestion_immutable BEFORE UPDATE OR DELETE ON workshop_revision_suggestion
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TABLE workshop_contribution_outcome (
 outcome_id uuid PRIMARY KEY REFERENCES contribution_outcome(id),
 task_id uuid NOT NULL UNIQUE REFERENCES workshop_revision_review(task_id)
);
CREATE TRIGGER workshop_contribution_outcome_immutable BEFORE UPDATE OR DELETE ON workshop_contribution_outcome
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON workshop_revision_suggestion,workshop_contribution_outcome FROM PUBLIC;
COMMIT;
