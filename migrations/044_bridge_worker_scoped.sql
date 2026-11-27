BEGIN;
-- All mailbox operations share the scheduler lock. No arbitrary SQL,
-- task mutation, budget reset or enable/unblock operation is exposed.
CREATE FUNCTION penny_bridge_rest_closed(p_enabled boolean,p_epoch bigint)
RETURNS boolean LANGUAGE plpgsql AS $rest$
DECLARE local_time timestamp;
BEGIN
    IF p_enabled IS FALSE THEN RETURN false; END IF;
    IF p_enabled IS NULL OR p_epoch IS NULL THEN RETURN true; END IF;
    local_time:=to_timestamp(p_epoch) AT TIME ZONE 'America/New_York';
    RETURN extract(year FROM local_time) NOT BETWEEN 2000 AND 2099
        OR extract(hour FROM local_time)<8;
EXCEPTION WHEN datetime_field_overflow OR numeric_value_out_of_range THEN
    RETURN true;
END;
$rest$;

CREATE FUNCTION penny_bridge_reserve()
RETURNS TABLE(kind text,question_id uuid,fence uuid,task_id uuid,delay bigint)
LANGUAGE plpgsql SECURITY DEFINER AS $reserve$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate bridge_control%ROWTYPE;
    t bigint;
    r record;
BEGIN
    delay:=60;
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR ctl.paused THEN kind:='paused'; RETURN NEXT; RETURN; END IF;
    SELECT * INTO gate FROM bridge_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.enabled OR gate.blocked_reason IS NOT NULL
    THEN kind:='paused'; RETURN NEXT; RETURN; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    IF gate.not_before>t THEN
        kind:='cooldown'; delay:=gate.not_before-t; RETURN NEXT; RETURN;
    END IF;
    UPDATE bridge_control SET not_before=t+60 WHERE singleton;
    WITH expired AS (
        UPDATE work_task SET state='expired'
          WHERE state='queued' AND deadline<=t RETURNING id
    ) INSERT INTO task_outcome SELECT id,'expired','deadline elapsed',t,0 FROM expired;
    SELECT b.question_id,b.fence,b.task_id,b.acked_at,
           w.state,m.enabled,m.local_member=b.local_member AS mapped
      INTO r FROM bridge_receipt b JOIN work_task w ON w.id=b.task_id
      JOIN bridge_member m ON m.cloud_owner=b.cloud_owner
      LEFT JOIN bridge_release a ON a.question_id=b.question_id
      WHERE b.expires_at>t AND b.remote_rejected_at IS NULL AND a.delivered_at IS NULL
      ORDER BY b.admitted_at,b.question_id LIMIT 1;
    IF NOT FOUND THEN
        kind:=CASE WHEN penny_bridge_rest_closed(ctl.rest_enabled,t)
                   THEN 'paused' ELSE 'claim' END;
    ELSIF NOT r.enabled OR NOT r.mapped THEN
        kind:='waiting';
    ELSE
        question_id:=r.question_id; fence:=r.fence; task_id:=r.task_id;
        kind:=CASE WHEN r.state IN ('failed','expired','canceled') THEN 'reject'
                   WHEN r.acked_at IS NULL THEN 'ack'
                   WHEN r.state='succeeded' THEN 'answer' ELSE 'waiting' END;
    END IF;
    RETURN NEXT;
END;
$reserve$;

CREATE FUNCTION penny_bridge_defer(p_seconds integer,p_block text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $defer$
DECLARE t bigint;
BEGIN
    IF p_seconds IS NULL OR p_seconds NOT BETWEEN 60 AND 86400 OR
       (p_block IS NOT NULL AND p_block NOT IN ('authentication','remote_conflict','local_integrity'))
    THEN RETURN false; END IF;
    PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    UPDATE bridge_control SET not_before=greatest(not_before,t+p_seconds),
        blocked_reason=coalesce(blocked_reason,p_block) WHERE singleton;
    RETURN FOUND;
END;
$defer$;

CREATE FUNCTION penny_bridge_reject(p_question uuid,p_fence uuid,p_task uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $reject$
DECLARE t bigint;
BEGIN
    PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    UPDATE bridge_receipt b SET remote_rejected_at=coalesce(b.remote_rejected_at,t)
      FROM work_task w,bridge_member m
      WHERE b.question_id=p_question AND b.fence=p_fence AND b.task_id=p_task
        AND w.id=b.task_id AND b.expires_at>t
        AND w.state IN ('failed','expired','canceled')
        AND m.cloud_owner=b.cloud_owner AND m.local_member=b.local_member AND m.enabled;
    RETURN FOUND;
END;
$reject$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_bridge_rest_closed(boolean,bigint)',
        'penny_bridge_reserve()','penny_bridge_defer(integer,text)',
        'penny_bridge_reject(uuid,uuid,uuid)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
