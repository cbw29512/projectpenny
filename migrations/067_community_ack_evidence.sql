BEGIN;
-- Separate append-only acknowledgment evidence; never mutate the intake receipt.
CREATE TABLE community_bridge_ack (
 cloud_id uuid PRIMARY KEY REFERENCES community_bridge_receipt(cloud_id),
 confirmed_at bigint NOT NULL CHECK(confirmed_at>=0)
);
CREATE TRIGGER community_bridge_ack_immutable BEFORE UPDATE OR DELETE ON community_bridge_ack
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON community_bridge_ack FROM PUBLIC;
CREATE FUNCTION penny_community_record_ack(p_cloud uuid,p_fence uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint; allowed boolean;
BEGIN
 SELECT NOT paused INTO allowed FROM scheduler_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN false; END IF;
 SELECT enabled INTO allowed FROM community_bridge_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN false; END IF;
 IF NOT penny_community_receipt_exists(p_cloud,p_fence) THEN RETURN false; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 INSERT INTO community_bridge_ack(cloud_id,confirmed_at)
 SELECT r.cloud_id,t FROM community_bridge_receipt r
 WHERE r.cloud_id=p_cloud AND r.fence=p_fence AND t<r.lease_until
 ON CONFLICT(cloud_id) DO NOTHING;
 RETURN EXISTS(SELECT 1 FROM community_bridge_ack WHERE cloud_id=p_cloud);
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 EXECUTE format('ALTER FUNCTION %I.penny_community_record_ack(uuid,uuid) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_community_record_ack(uuid,uuid) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
