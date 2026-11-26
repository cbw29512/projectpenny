BEGIN;
-- Extend the existing world journal, rather than creating a competing inventory.
ALTER TABLE penny_world_event DROP CONSTRAINT penny_world_event_asset_id_check;
ALTER TABLE penny_world_event ADD CHECK(asset_id IN ('plant-v1','mug-v1','plum-outfit-v1','bit-v1'));
ALTER TABLE penny_world_event DROP CONSTRAINT penny_world_event_slot_check;
ALTER TABLE penny_world_event ADD CHECK(slot IN ('left-shelf','right-shelf','desk-corner','outfit','bit-dock'));
ALTER TABLE penny_world_event ADD COLUMN reward_source_sha256 text;
ALTER TABLE penny_world_event ADD CHECK (
  CASE WHEN asset_id='bit-v1' AND action='acquire'
    THEN reward_source_sha256 IS NOT NULL AND reward_source_sha256 ~ '^[a-f0-9]{64}$'
    ELSE reward_source_sha256 IS NULL END
);
ALTER TABLE penny_world_event ADD CHECK (
  CASE WHEN asset_id='bit-v1' AND action IN ('place','move')
    THEN slot IS NOT NULL AND slot='bit-dock'
    ELSE slot IS DISTINCT FROM 'bit-dock' END
);
COMMIT;
