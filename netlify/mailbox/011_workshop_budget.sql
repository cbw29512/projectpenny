BEGIN;
-- Two fixed rows, shared across serverless instances. No per-IP records.
CREATE TABLE workshop_attempt_budget (
 op text PRIMARY KEY CHECK(op IN ('read','write')),
 minute_bucket bigint NOT NULL DEFAULT 0 CHECK(minute_bucket>=0),
 minute_count integer NOT NULL DEFAULT 0 CHECK(minute_count>=0),
 day_bucket bigint NOT NULL DEFAULT 0 CHECK(day_bucket>=0),
 day_count integer NOT NULL DEFAULT 0 CHECK(day_count>=0)
);
INSERT INTO workshop_attempt_budget(op) VALUES ('read'),('write');

CREATE FUNCTION workshop_take_attempt(p_op text)
RETURNS boolean LANGUAGE plpgsql AS $body$
DECLARE
 g workshop_attempt_budget%ROWTYPE;
 at_epoch bigint; minute_now bigint; day_now bigint;
 minute_limit integer; day_limit integer;
BEGIN
 CASE p_op
  WHEN 'read' THEN minute_limit:=60; day_limit:=1800;
  WHEN 'write' THEN minute_limit:=2; day_limit:=1440;
  ELSE RETURN false;
 END CASE;
 IF NOT EXISTS(SELECT 1 FROM workshop_observation WHERE singleton AND enabled)
 THEN RETURN false; END IF;
 SELECT * INTO g FROM workshop_attempt_budget WHERE op=p_op FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 at_epoch:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 minute_now:=greatest(g.minute_bucket,at_epoch/60);
 day_now:=greatest(g.day_bucket,at_epoch/86400);
 IF (minute_now=g.minute_bucket AND g.minute_count>=minute_limit)
 OR (day_now=g.day_bucket AND g.day_count>=day_limit) THEN RETURN false; END IF;
 UPDATE workshop_attempt_budget SET minute_bucket=minute_now,
 minute_count=CASE WHEN minute_now>g.minute_bucket THEN 1 ELSE g.minute_count+1 END,
 day_bucket=day_now,
 day_count=CASE WHEN day_now>g.day_bucket THEN 1 ELSE g.day_count+1 END
 WHERE op=p_op;
 RETURN true;
END;
$body$;

CREATE FUNCTION workshop_allow_read()
RETURNS boolean LANGUAGE sql SECURITY DEFINER AS $body$
 SELECT workshop_take_attempt('read');
$body$;
CREATE FUNCTION workshop_allow_write()
RETURNS boolean LANGUAGE sql SECURITY DEFINER AS $body$
 SELECT workshop_take_attempt('write');
$body$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
 IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
 EXECUTE format('REVOKE ALL ON TABLE %I.workshop_attempt_budget FROM PUBLIC',ns);
 FOREACH signature IN ARRAY ARRAY['workshop_take_attempt(text)','workshop_allow_read()','workshop_allow_write()'] LOOP
  EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
  EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
 END LOOP;
END;
$secure$;
COMMIT;
