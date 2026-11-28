BEGIN;
-- Narrow receipt verification, not admission. Never returns member or idea data.
CREATE FUNCTION penny_community_receipt_exists(p_cloud uuid,p_fence uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint;
BEGIN
 PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 RETURN EXISTS(
  SELECT 1 FROM community_bridge_receipt r
  JOIN bridge_member m ON m.cloud_owner=r.cloud_owner
    AND m.local_member=r.local_member AND m.enabled
  JOIN community_suggestion s ON s.id=r.suggestion_id AND s.member_id=r.local_member
  WHERE r.cloud_id=p_cloud AND r.fence=p_fence
    AND s.submitted_at>=0 AND s.submitted_at<=r.admitted_at
    AND r.admitted_at<=t AND t<r.lease_until AND r.lease_until<=r.expires_at
    AND s.body_sha256=encode(sha256(convert_to(s.body,'UTF8')),'hex')
 );
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 EXECUTE format('ALTER FUNCTION %I.penny_community_receipt_exists(uuid,uuid) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_community_receipt_exists(uuid,uuid) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
