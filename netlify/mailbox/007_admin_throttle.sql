BEGIN;
-- Dedicated fixed-size counters: public traffic cannot exhaust admin budget.
CREATE TABLE mailbox_admin_budget (
    op text PRIMARY KEY CHECK(op IN ('status','pause')),
    minute_bucket bigint NOT NULL DEFAULT 0,
    minute_count integer NOT NULL DEFAULT 0 CHECK(minute_count>=0),
    day_bucket bigint NOT NULL DEFAULT 0,
    day_count integer NOT NULL DEFAULT 0 CHECK(day_count>=0)
);
INSERT INTO mailbox_admin_budget(op) VALUES ('status'),('pause');
CREATE FUNCTION mailbox_admin_allow(p_admin uuid,p_op text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $admin_allow$
DECLARE
    g mailbox_admin_budget%ROWTYPE;
    at_time timestamptz;
    m bigint;
    d bigint;
    minute_limit integer;
    day_limit integer;
BEGIN
    CASE p_op
      WHEN 'status' THEN minute_limit:=12; day_limit:=360;
      WHEN 'pause' THEN minute_limit:=6; day_limit:=60;
      ELSE RETURN false;
    END CASE;
    IF NOT EXISTS(SELECT 1 FROM mailbox_admin WHERE id=p_admin AND enabled)
    THEN RETURN false; END IF;
    SELECT * INTO g FROM mailbox_admin_budget WHERE op=p_op FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    at_time:=clock_timestamp();
    m:=greatest(g.minute_bucket,floor(extract(epoch FROM at_time)/60)::bigint);
    d:=greatest(g.day_bucket,floor(extract(epoch FROM at_time)/86400)::bigint);
    IF (g.minute_bucket=m AND g.minute_count>=minute_limit)
       OR (g.day_bucket=d AND g.day_count>=day_limit) THEN RETURN false; END IF;
    UPDATE mailbox_admin_budget SET
        minute_count=CASE WHEN minute_bucket<m THEN 1 ELSE minute_count+1 END,
        minute_bucket=m,
        day_count=CASE WHEN day_bucket<d THEN 1 ELSE day_count+1 END,
        day_bucket=d WHERE op=p_op;
    RETURN true;
END;
$admin_allow$;
DO $secure_admin_limit$
DECLARE ns name:=current_schema();
BEGIN
    IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
    EXECUTE format('REVOKE ALL ON TABLE %I.mailbox_admin_budget FROM PUBLIC',ns);
    EXECUTE format('ALTER FUNCTION %I.mailbox_admin_allow(uuid,text) SET search_path TO pg_catalog,%I,pg_temp',ns,ns);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.mailbox_admin_allow(uuid,text) FROM PUBLIC',ns);
END;
$secure_admin_limit$;
COMMIT;
