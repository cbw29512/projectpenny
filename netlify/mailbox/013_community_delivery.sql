BEGIN;
-- One transfer per claim, with no automatic reissue after an uncertain delivery.
ALTER TABLE community_mailbox_suggestion
 ADD COLUMN fence uuid UNIQUE,
 ADD COLUMN lease_until timestamptz,
 ADD COLUMN delivered_at timestamptz,
 ADD CONSTRAINT community_delivery_shape CHECK (
   (fence IS NULL AND lease_until IS NULL AND delivered_at IS NULL)
   OR (fence IS NOT NULL AND lease_until IS NOT NULL
       AND lease_until<=expires_at AND lease_until>submitted_at
       AND (delivered_at IS NULL OR delivered_at BETWEEN submitted_at AND lease_until))
 );
CREATE FUNCTION community_mailbox_claim()
RETURNS TABLE(suggestion_id uuid,owner_id uuid,request_key uuid,body text,
 fence uuid,expires_at timestamptz,lease_until timestamptz)
LANGUAGE plpgsql AS $body$
DECLARE gate boolean; at_time timestamptz; picked uuid;
BEGIN
 SELECT enabled INTO gate FROM community_mailbox_control WHERE singleton FOR UPDATE;
 IF gate IS DISTINCT FROM true THEN RETURN; END IF;
 at_time:=clock_timestamp();
 IF EXISTS(SELECT 1 FROM community_mailbox_suggestion s
 WHERE s.fence IS NOT NULL AND s.delivered_at IS NULL AND s.lease_until>at_time)
 THEN RETURN; END IF;
 SELECT s.id INTO picked FROM community_mailbox_suggestion s
 JOIN mailbox_member m ON m.id=s.owner_id AND m.enabled
 WHERE s.fence IS NULL AND s.expires_at>at_time AND s.submitted_at<=at_time
 ORDER BY s.submitted_at,s.id LIMIT 1;
 IF picked IS NULL THEN RETURN; END IF;
 RETURN QUERY UPDATE community_mailbox_suggestion s
 SET fence=gen_random_uuid(),lease_until=least(s.expires_at,at_time+interval '15 minutes')
 WHERE s.id=picked RETURNING s.id,s.owner_id,s.request_key,s.body,s.fence,s.expires_at,s.lease_until;
END;
$body$;
-- A trusted future adapter may acknowledge only after a durable local receipt.
CREATE FUNCTION community_mailbox_ack(p_id uuid,p_fence uuid)
RETURNS boolean LANGUAGE plpgsql AS $body$
DECLARE at_time timestamptz; row_data community_mailbox_suggestion%ROWTYPE;
BEGIN
 PERFORM 1 FROM community_mailbox_control WHERE singleton FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 at_time:=clock_timestamp();
 SELECT * INTO row_data FROM community_mailbox_suggestion s WHERE s.id=p_id AND s.fence=p_fence;
 IF NOT FOUND THEN RETURN false; END IF;
 IF NOT EXISTS(SELECT 1 FROM mailbox_member m WHERE m.id=row_data.owner_id AND m.enabled)
 THEN RETURN false; END IF;
 IF row_data.delivered_at IS NOT NULL THEN RETURN true; END IF;
 IF row_data.lease_until<=at_time OR row_data.expires_at<=at_time
 OR row_data.submitted_at>at_time THEN RETURN false; END IF;
 UPDATE community_mailbox_suggestion SET delivered_at=at_time WHERE id=p_id;
 RETURN true;
END;
$body$;
DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
 IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
 FOREACH signature IN ARRAY ARRAY['community_mailbox_claim()','community_mailbox_ack(uuid,uuid)'] LOOP
  EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
  EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
 END LOOP;
END;
$secure$;
COMMIT;
