BEGIN;
-- CREATE OR REPLACE resets routine configuration unless explicitly restated.
-- Restore the pinned search paths for both replaced community routines.
DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
 IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
 FOREACH signature IN ARRAY ARRAY['penny_community_reserve()','penny_community_recover()'] LOOP
  EXECUTE format('ALTER FUNCTION %I.%s SECURITY DEFINER',ns,signature);
  EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
  EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
 END LOOP;
END;
$secure$;
COMMIT;
