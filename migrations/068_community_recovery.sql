BEGIN;
-- Recovery has its own durable throttle; never reset the claim cooldown.
ALTER TABLE community_bridge_control ADD COLUMN recovery_not_before bigint NOT NULL DEFAULT 0;
CREATE FUNCTION penny_community_recover()
RETURNS TABLE(cloud_id uuid,fence uuid) LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint; allowed boolean; picked record;
BEGIN
 SELECT NOT paused INTO allowed FROM scheduler_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 SELECT enabled AND recovery_not_before<=t INTO allowed FROM community_bridge_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN; END IF;
 SELECT r.cloud_id,r.fence INTO picked FROM community_bridge_receipt r
 LEFT JOIN community_bridge_ack a ON a.cloud_id=r.cloud_id
 WHERE a.cloud_id IS NULL AND r.lease_until>t+15
 ORDER BY r.admitted_at,r.cloud_id LIMIT 1;
 IF NOT FOUND THEN RETURN; END IF;
 IF NOT penny_community_receipt_exists(picked.cloud_id,picked.fence) THEN RETURN; END IF;
 UPDATE community_bridge_control SET recovery_not_before=t+60 WHERE singleton;
 RETURN QUERY SELECT picked.cloud_id,picked.fence;
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 EXECUTE format('ALTER FUNCTION %I.penny_community_recover() SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_community_recover() FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
