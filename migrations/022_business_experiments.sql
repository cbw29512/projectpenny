BEGIN;
-- Private, zero-additional-cash experiments. No external execution authority.
CREATE TABLE business_opportunity (
 id uuid PRIMARY KEY,
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 category text NOT NULL CHECK(category IN ('digital_product','content','software_utility','service_research')),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
 hypothesis text NOT NULL CHECK(length(hypothesis) BETWEEN 1 AND 1000),
 metric text NOT NULL CHECK(metric IN ('qualified_interest','prototype_checks_passed','validated_requirements')),
 target integer NOT NULL CHECK(target BETWEEN 1 AND 10000),
 duration_seconds integer NOT NULL CHECK(duration_seconds BETWEEN 60 AND 604800),
 additional_cash_cents bigint NOT NULL DEFAULT 0 CHECK(additional_cash_cents=0),
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 reviewer_id uuid NOT NULL,
 created_at bigint NOT NULL,
 review_until bigint NOT NULL CHECK(review_until>created_at AND review_until-created_at<=604800),
 policy_version text NOT NULL
);
CREATE TABLE business_experiment_event (
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
 id uuid PRIMARY KEY,
 opportunity_id uuid NOT NULL REFERENCES business_opportunity(id),
 action text NOT NULL CHECK(action IN ('approved','rejected','started','measured','stopped')),
 reviewer_id uuid NOT NULL,
 recorded_at bigint NOT NULL,
 deadline bigint,
 observed_at bigint,
 measured_count integer CHECK(measured_count BETWEEN 0 AND 1000000),
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 policy_version text NOT NULL,
 UNIQUE(opportunity_id,action),
 CHECK((action='started' AND deadline IS NOT NULL AND deadline>recorded_at)
    OR (action<>'started' AND deadline IS NULL)),
 CHECK((action='measured' AND observed_at IS NOT NULL AND measured_count IS NOT NULL
        AND observed_at<=recorded_at)
    OR (action<>'measured' AND observed_at IS NULL AND measured_count IS NULL))
);
CREATE INDEX business_event_latest ON business_experiment_event(opportunity_id,sequence DESC);
CREATE TRIGGER business_opportunity_immutable BEFORE UPDATE OR DELETE ON business_opportunity
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
CREATE TRIGGER business_event_immutable BEFORE UPDATE OR DELETE ON business_experiment_event
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON business_opportunity,business_experiment_event FROM PUBLIC;
COMMIT;
