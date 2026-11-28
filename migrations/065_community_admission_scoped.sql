BEGIN;
-- First scoped admission slice deliberately restricts input to printable ASCII.
-- Unicode casefold parity with Python is not assumed in PostgreSQL 16.
CREATE TABLE community_bridge_control (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 enabled boolean NOT NULL DEFAULT false
);
INSERT INTO community_bridge_control DEFAULT VALUES;
REVOKE ALL ON community_bridge_control FROM PUBLIC;
CREATE FUNCTION penny_community_admit(p_cloud uuid,p_owner uuid,p_key uuid,p_fence uuid,
 p_body text,p_expiry bigint,p_lease bigint)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $body$
DECLARE t bigint; member uuid; old community_bridge_receipt%ROWTYPE;
 s community_suggestion%ROWTYPE; norm text; raw_hash text; exact_hash text; dup_hash text;
 total bigint; daily bigint; pending bigint; owner_daily bigint; owner_pending bigint;
 sid uuid; gate boolean;
BEGIN
 IF p_cloud IS NULL OR p_owner IS NULL OR p_key IS NULL OR p_fence IS NULL
 OR '00000000-0000-0000-0000-000000000000'::uuid IN (p_cloud,p_owner,p_key,p_fence)
 OR p_body IS NULL OR length(p_body) NOT BETWEEN 1 AND 500
 OR p_body COLLATE "C" ~ '[^ -~]' OR p_expiry IS NULL OR p_lease IS NULL
 THEN RETURN false; END IF;
 norm:=regexp_replace(btrim(p_body),' +',' ','g');
 IF length(regexp_replace(norm COLLATE "C",'[^A-Za-z0-9]','','g'))<3 THEN RETURN false; END IF;
 raw_hash:=encode(sha256(convert_to(p_body,'UTF8')),'hex');
 exact_hash:=encode(sha256(convert_to(norm,'UTF8')),'hex');
 dup_hash:=encode(sha256(convert_to(lower(norm COLLATE "C"),'UTF8')),'hex');
 SELECT NOT paused INTO gate FROM scheduler_control WHERE singleton FOR UPDATE;
 IF gate IS DISTINCT FROM true THEN RETURN false; END IF;
 SELECT enabled INTO gate FROM community_bridge_control WHERE singleton FOR UPDATE;
 IF gate IS DISTINCT FROM true THEN RETURN false; END IF;
 t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 IF p_lease<=t OR p_lease>t+900 OR p_expiry<p_lease OR p_expiry>t+3600 THEN RETURN false; END IF;
 SELECT local_member INTO member FROM bridge_member WHERE cloud_owner=p_owner AND enabled FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT * INTO old FROM community_bridge_receipt WHERE cloud_id=p_cloud;
 IF FOUND THEN
  IF (old.cloud_owner,old.local_member,old.request_key,old.fence,old.payload_sha256,old.expires_at,old.lease_until)
   IS DISTINCT FROM (p_owner,member,p_key,p_fence,raw_hash,p_expiry,p_lease) THEN RETURN false; END IF;
  RETURN penny_community_receipt_exists(p_cloud,p_fence) AND EXISTS(
   SELECT 1 FROM community_suggestion WHERE id=old.suggestion_id AND duplicate_sha256=dup_hash);
 END IF;
 IF EXISTS(SELECT 1 FROM community_bridge_receipt WHERE fence=p_fence OR (cloud_owner=p_owner AND request_key=p_key))
 OR (SELECT count(*) FROM community_bridge_receipt)>=4096 THEN RETURN false; END IF;
 SELECT * INTO s FROM community_suggestion WHERE member_id=member AND request_key=p_key::text;
 IF FOUND THEN
  IF s.body_sha256<>exact_hash THEN RETURN false; END IF;
 ELSE
  SELECT * INTO s FROM community_suggestion WHERE member_id=member AND duplicate_sha256=dup_hash;
 END IF;
 IF s.id IS NOT NULL THEN
  IF s.submitted_at<0 OR s.submitted_at>t OR s.duplicate_sha256<>dup_hash
  OR s.body_sha256<>encode(sha256(convert_to(s.body,'UTF8')),'hex')
  THEN RETURN false; END IF;
  sid:=s.id;
 ELSE
  WITH intake AS (
   SELECT s0.member_id,s0.submitted_at,r.suggestion_id IS NULL AS pending
   FROM community_suggestion s0 LEFT JOIN community_suggestion_review r ON r.suggestion_id=s0.id
   UNION ALL
   SELECT f.member_id,f.submitted_at,f.withdrawn_at IS NULL AND v.feedback_id IS NULL
   FROM workshop_feedback f LEFT JOIN workshop_feedback_review v ON v.feedback_id=f.id
  )
  SELECT count(*),count(*) FILTER(WHERE submitted_at>t-86400),
   count(*) FILTER(WHERE intake.pending),
   count(*) FILTER(WHERE member_id=member AND submitted_at>t-86400),
   count(*) FILTER(WHERE member_id=member AND intake.pending)
  INTO total,daily,pending,owner_daily,owner_pending FROM intake;
  IF total>=4096 OR daily>=60 OR pending>=100 OR owner_daily>=3 OR owner_pending>=3 THEN RETURN false; END IF;
  sid:=gen_random_uuid();
  INSERT INTO community_suggestion VALUES(sid,member,p_key::text,norm,exact_hash,dup_hash,t,'guardian-v0.22');
 END IF;
 INSERT INTO community_bridge_receipt VALUES(p_cloud,p_owner,member,p_key,p_fence,raw_hash,sid,p_expiry,p_lease,t);
 RETURN true;
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 EXECUTE format('ALTER FUNCTION %I.penny_community_admit(uuid,uuid,uuid,uuid,text,bigint,bigint) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_community_admit(uuid,uuid,uuid,uuid,text,bigint,bigint) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
