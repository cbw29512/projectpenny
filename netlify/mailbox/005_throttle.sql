BEGIN;
-- Fixed-size global buckets, plus two buckets per provisioned member.
-- Counts are attempts admitted to the HTTP core, not accepted AI jobs.
CREATE TABLE mailbox_attempt_global (
    op text PRIMARY KEY CHECK(op IN ('submit','read','claim','ack','answer','reject')),
    minute_bucket bigint NOT NULL DEFAULT 0,
    minute_count integer NOT NULL DEFAULT 0 CHECK(minute_count>=0),
    day_bucket bigint NOT NULL DEFAULT 0,
    day_count integer NOT NULL DEFAULT 0 CHECK(day_count>=0)
);
INSERT INTO mailbox_attempt_global(op) VALUES
    ('submit'),('read'),('claim'),('ack'),('answer'),('reject');
CREATE TABLE mailbox_attempt_member (
    owner_id uuid NOT NULL REFERENCES mailbox_member(id) ON DELETE CASCADE,
    op text NOT NULL CHECK(op IN ('submit','read')),
    minute_bucket bigint NOT NULL,
    minute_count integer NOT NULL CHECK(minute_count>0),
    PRIMARY KEY(owner_id,op)
);

-- Private helper; caller wrappers constrain the available operation.
-- Global row lock serializes check and increment across all instances.
CREATE FUNCTION mailbox_take_attempt(p_op text,p_owner uuid)
RETURNS boolean LANGUAGE plpgsql AS $attempt_body$
DECLARE
    g mailbox_attempt_global%ROWTYPE;
    minute_now bigint;
    day_now bigint;
    at_time timestamptz;
    per_minute integer;
    per_day integer;
    per_owner integer;
BEGIN
    CASE p_op
      WHEN 'submit' THEN per_minute:=40; per_day:=600; per_owner:=6;
      WHEN 'read' THEN per_minute:=120; per_day:=3600; per_owner:=12;
      WHEN 'claim' THEN per_minute:=6; per_day:=1440;
      WHEN 'ack' THEN per_minute:=12; per_day:=360;
      WHEN 'answer' THEN per_minute:=12; per_day:=360;
      WHEN 'reject' THEN per_minute:=12; per_day:=360;
      ELSE RETURN false;
    END CASE;
    IF p_op IN ('submit','read') THEN
        IF p_owner IS NULL OR NOT EXISTS(
            SELECT 1 FROM mailbox_member WHERE id=p_owner AND enabled
        ) THEN RETURN false; END IF;
    ELSIF p_owner IS NOT NULL THEN RETURN false;
    END IF;

    SELECT * INTO g FROM mailbox_attempt_global WHERE op=p_op FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    -- DB clock after locking; never reset a bucket on backward clock movement.
    at_time:=clock_timestamp();
    minute_now:=greatest(g.minute_bucket,floor(extract(epoch FROM at_time)/60)::bigint);
    day_now:=greatest(g.day_bucket,floor(extract(epoch FROM at_time)/86400)::bigint);
    IF (g.minute_bucket=minute_now AND g.minute_count>=per_minute)
       OR (g.day_bucket=day_now AND g.day_count>=per_day) THEN RETURN false; END IF;
    IF p_owner IS NOT NULL THEN
        INSERT INTO mailbox_attempt_member AS m(owner_id,op,minute_bucket,minute_count)
        VALUES(p_owner,p_op,minute_now,1)
        ON CONFLICT(owner_id,op) DO UPDATE SET
            minute_bucket=excluded.minute_bucket,
            minute_count=CASE WHEN m.minute_bucket<excluded.minute_bucket THEN 1
                              ELSE m.minute_count+1 END
        WHERE m.minute_bucket<=excluded.minute_bucket
          AND (m.minute_bucket<excluded.minute_bucket OR m.minute_count<per_owner);
        IF NOT FOUND THEN RETURN false; END IF;
    END IF;
    UPDATE mailbox_attempt_global SET
        minute_count=CASE WHEN minute_bucket<minute_now THEN 1 ELSE minute_count+1 END,
        minute_bucket=minute_now,
        day_count=CASE WHEN day_bucket<day_now THEN 1 ELSE day_count+1 END,
        day_bucket=day_now WHERE op=p_op;
    RETURN true;
END;
$attempt_body$;

CREATE FUNCTION mailbox_allow_member(p_owner uuid,p_op text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $member_body$
BEGIN
    IF p_owner IS NULL OR p_op IS NULL OR p_op NOT IN ('submit','read') THEN RETURN false; END IF;
    RETURN mailbox_take_attempt(p_op,p_owner);
END;
$member_body$;

CREATE FUNCTION mailbox_allow_bridge(p_op text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $bridge_body$
BEGIN
    IF p_op IS NULL OR p_op NOT IN ('claim','ack','answer','reject') THEN RETURN false; END IF;
    RETURN mailbox_take_attempt(p_op,NULL);
END;
$bridge_body$;

DO $secure_attempt$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%' THEN
        RAISE EXCEPTION 'dedicated mailbox schema required';
    END IF;
    EXECUTE format('REVOKE ALL ON TABLE %I.mailbox_attempt_global,%I.mailbox_attempt_member FROM PUBLIC',ns,ns);
    FOREACH signature IN ARRAY ARRAY['mailbox_take_attempt(text,uuid)',
        'mailbox_allow_member(uuid,text)','mailbox_allow_bridge(text)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure_attempt$;
COMMIT;
