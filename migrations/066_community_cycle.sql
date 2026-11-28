BEGIN;
-- Reserve a durable interval before any network claim, even after process crash.
ALTER TABLE community_bridge_control ADD COLUMN not_before bigint NOT NULL DEFAULT 0;
CREATE FUNCTION penny_community_reserve()
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint; allowed boolean;
BEGIN
 SELECT NOT paused INTO allowed FROM scheduler_control WHERE singleton FOR UPDATE;
 IF allowed IS DISTINCT FROM true THEN RETURN false; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 UPDATE community_bridge_control SET not_before=t+900
 WHERE singleton AND enabled AND not_before<=t;
 RETURN FOUND;
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 EXECUTE format('ALTER FUNCTION %I.penny_community_reserve() SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_community_reserve() FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
