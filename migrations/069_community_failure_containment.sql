BEGIN;
ALTER TABLE community_bridge_control ADD COLUMN provider_not_before bigint NOT NULL DEFAULT 0,
 ADD COLUMN blocked_reason text CHECK(blocked_reason IN ('authentication','remote_conflict','local_integrity'));
CREATE OR REPLACE FUNCTION penny_community_reserve()
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint; allowed boolean;
BEGIN
 SELECT NOT paused INTO allowed FROM scheduler_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN false; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 UPDATE community_bridge_control SET not_before=t+900
 WHERE singleton AND enabled AND blocked_reason IS NULL AND not_before<=t AND provider_not_before<=t;
 RETURN FOUND;
END;
$body$;

CREATE OR REPLACE FUNCTION penny_community_recover()
RETURNS TABLE(cloud_id uuid,fence uuid) LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint; allowed boolean; picked record;
BEGIN
 SELECT NOT paused INTO allowed FROM scheduler_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 SELECT enabled AND blocked_reason IS NULL AND provider_not_before<=t AND recovery_not_before<=t INTO allowed FROM community_bridge_control WHERE singleton FOR UPDATE;
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

CREATE FUNCTION penny_community_defer(p_seconds integer,p_block text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint;
BEGIN
 IF p_seconds IS NULL OR p_seconds NOT BETWEEN 60 AND 86400 OR
 (p_block IS NOT NULL AND p_block NOT IN ('authentication','remote_conflict','local_integrity'))
 THEN RETURN false; END IF;
 PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 UPDATE community_bridge_control SET provider_not_before=greatest(provider_not_before,t+p_seconds),
 blocked_reason=coalesce(blocked_reason,p_block) WHERE singleton;
 RETURN FOUND;
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 EXECUTE format('ALTER FUNCTION %I.penny_community_defer(integer,text) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_community_defer(integer,text) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
