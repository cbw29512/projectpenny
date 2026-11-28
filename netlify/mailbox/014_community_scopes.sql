BEGIN;
-- Narrow cloud capabilities only; no direct table grants.
DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
 IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
 FOREACH signature IN ARRAY ARRAY['community_mailbox_submit(uuid,uuid,text)',
     'community_mailbox_claim()','community_mailbox_ack(uuid,uuid)'] LOOP
  EXECUTE format('ALTER FUNCTION %I.%s SECURITY DEFINER',ns,signature);
  EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
  EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
 END LOOP;
END;
$secure$;
COMMIT;
