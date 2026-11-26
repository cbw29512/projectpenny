BEGIN;
-- Private virtual-only world history. No purchase, entitlement or publication authority.
CREATE TABLE penny_world_event (
 revision integer PRIMARY KEY CHECK(revision BETWEEN 1 AND 2048),
 event_id uuid NOT NULL UNIQUE,
 source_ref text NOT NULL UNIQUE CHECK(source_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 baseline text NOT NULL CHECK(baseline='preview-v1'),
 prior_revision integer NOT NULL CHECK(prior_revision=revision-1),
 action text NOT NULL CHECK(action IN ('acquire','place','move','store','equip','unequip','remove')),
 asset_id text NOT NULL CHECK(asset_id IN ('plant-v1','mug-v1','plum-outfit-v1')),
 slot text CHECK(slot IN ('left-shelf','right-shelf','desk-corner','outfit')),
 reviewer_id uuid NOT NULL,
 evidence_ref text NOT NULL CHECK(evidence_ref ~ '^[A-Za-z0-9_.:/-]{1,128}$'),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[a-f0-9]{64}$'),
 evidence_size integer NOT NULL CHECK(evidence_size BETWEEN 1 AND 16384),
 recorded_at bigint NOT NULL,
 policy_version text NOT NULL
);
CREATE TRIGGER penny_world_event_immutable BEFORE UPDATE OR DELETE ON penny_world_event
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON penny_world_event FROM PUBLIC;
COMMIT;
