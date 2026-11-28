BEGIN;
-- Separate suggestion transport, never a conversation or executable task.
CREATE TABLE community_mailbox_control (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 enabled boolean NOT NULL DEFAULT false
);
INSERT INTO community_mailbox_control DEFAULT VALUES;
CREATE TABLE community_mailbox_suggestion (
 id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES mailbox_member(id),
 request_key uuid NOT NULL,
 body text NOT NULL CHECK(length(body) BETWEEN 1 AND 500 AND octet_length(body)<=2000),
 submitted_at timestamptz NOT NULL,
 expires_at timestamptz NOT NULL CHECK(expires_at>submitted_at),
 UNIQUE(owner_id,request_key)
);
CREATE INDEX community_mailbox_recent ON community_mailbox_suggestion(submitted_at);
CREATE INDEX community_mailbox_owner_recent ON community_mailbox_suggestion(owner_id,submitted_at);

-- Admission only. No claim, bridge delivery or public endpoint in this migration.
CREATE FUNCTION community_mailbox_submit(p_owner uuid,p_key uuid,p_body text)
RETURNS TABLE(status text,suggestion_id uuid,replayed boolean)
LANGUAGE plpgsql AS $body$
DECLARE gate boolean; at_time timestamptz; old_row community_mailbox_suggestion%ROWTYPE;
 new_id uuid;
BEGIN
 IF p_owner IS NULL OR p_key IS NULL OR p_body IS NULL
 OR p_owner='00000000-0000-0000-0000-000000000000'
 OR p_key='00000000-0000-0000-0000-000000000000'
 OR length(p_body)>500 OR octet_length(p_body)>2000
 OR p_body !~ '[^[:space:]]' OR p_body ~ '[[:cntrl:]]'
 THEN RETURN QUERY SELECT 'invalid'::text,NULL::uuid,false; RETURN; END IF;
 SELECT enabled INTO gate FROM community_mailbox_control WHERE singleton FOR UPDATE;
 at_time:=clock_timestamp();
 IF NOT EXISTS(SELECT 1 FROM mailbox_member WHERE id=p_owner AND enabled)
 THEN RETURN QUERY SELECT 'denied'::text,NULL::uuid,false; RETURN; END IF;
 IF gate IS DISTINCT FROM true
 THEN RETURN QUERY SELECT 'paused'::text,NULL::uuid,false; RETURN; END IF;
 SELECT * INTO old_row FROM community_mailbox_suggestion WHERE owner_id=p_owner AND request_key=p_key;
 IF FOUND THEN
  IF old_row.body<>p_body THEN RETURN QUERY SELECT 'conflict'::text,NULL::uuid,false;
  ELSIF old_row.expires_at<=at_time THEN RETURN QUERY SELECT 'expired'::text,NULL::uuid,false;
  ELSE RETURN QUERY SELECT 'accepted'::text,old_row.id,true; END IF;
  RETURN;
 END IF;
 IF (SELECT count(*) FROM community_mailbox_suggestion WHERE owner_id=p_owner AND submitted_at>at_time-interval '24 hours')>=3
 THEN RETURN QUERY SELECT 'member_quota'::text,NULL::uuid,false; RETURN; END IF;
 IF (SELECT count(*) FROM community_mailbox_suggestion WHERE submitted_at>at_time-interval '24 hours')>=60
 OR (SELECT count(*) FROM community_mailbox_suggestion WHERE expires_at>at_time)>=100
 OR (SELECT count(*) FROM community_mailbox_suggestion)>=512
 THEN RETURN QUERY SELECT 'full'::text,NULL::uuid,false; RETURN; END IF;
 new_id:=gen_random_uuid();
 INSERT INTO community_mailbox_suggestion VALUES(new_id,p_owner,p_key,p_body,at_time,at_time+interval '1 hour');
 RETURN QUERY SELECT 'accepted'::text,new_id,false;
END;
$body$;
-- No grants yet. Invoker-only until reviewed role provisioning.
DO $secure$
DECLARE ns name:=current_schema();
BEGIN
 IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
 EXECUTE format('REVOKE ALL ON TABLE %I.community_mailbox_control,%I.community_mailbox_suggestion FROM PUBLIC',ns,ns);
 EXECUTE format('ALTER FUNCTION %I.community_mailbox_submit(uuid,uuid,text) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
 EXECUTE format('REVOKE ALL ON FUNCTION %I.community_mailbox_submit(uuid,uuid,text) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
