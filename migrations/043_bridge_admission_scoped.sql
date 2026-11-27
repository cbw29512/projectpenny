BEGIN;
-- Worker accepts only mapped visitor questions. No arbitrary task class,
-- entitlement, member-memory scope, deadline or operator fields from caller.
CREATE FUNCTION penny_bridge_admit(p_question uuid,p_owner uuid,p_fence uuid,
                                    p_expiry bigint,p_text text)
RETURNS TABLE(status text,task_id uuid,replayed boolean)
LANGUAGE plpgsql SECURITY DEFINER AS $admit$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate bridge_control%ROWTYPE;
    old bridge_receipt%ROWTYPE;
    t bigint;
    member uuid;
    digest text;
    tier smallint;
    local_time timestamp;
    hourly bigint;
    daily bigint;
BEGIN
    replayed:=false;
    IF p_question IS NULL OR p_owner IS NULL OR p_fence IS NULL OR
       p_question='00000000-0000-0000-0000-000000000000'::uuid OR
       p_owner='00000000-0000-0000-0000-000000000000'::uuid OR
       p_fence='00000000-0000-0000-0000-000000000000'::uuid OR
       p_expiry IS NULL OR p_text IS NULL OR length(p_text) NOT BETWEEN 1 AND 2000
       OR octet_length(p_text)>8000 OR p_text !~ '[^[:space:]]'
    THEN status:='invalid'; RETURN NEXT; RETURN; END IF;
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR ctl.paused THEN status:='paused'; RETURN NEXT; RETURN; END IF;
    SELECT * INTO gate FROM bridge_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.enabled OR gate.blocked_reason IS NOT NULL
    THEN status:='paused'; RETURN NEXT; RETURN; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    IF p_expiry<=t+5 OR p_expiry>t+900
    THEN status:='expired'; RETURN NEXT; RETURN; END IF;
    SELECT m.local_member INTO member FROM bridge_member m
      WHERE m.cloud_owner=p_owner AND m.enabled FOR UPDATE;
    IF NOT FOUND THEN status:='denied'; RETURN NEXT; RETURN; END IF;
    digest:=encode(sha256(convert_to(p_text,'UTF8')),'hex');
    SELECT * INTO old FROM bridge_receipt r WHERE r.question_id=p_question;
    IF FOUND THEN
        IF (old.cloud_owner,old.local_member,old.fence,old.payload_sha256,old.expires_at)
           IS DISTINCT FROM (p_owner,member,p_fence,digest,p_expiry)
        THEN status:='conflict';
        ELSE status:='accept'; task_id:=old.task_id; replayed:=true; END IF;
        RETURN NEXT; RETURN;
    END IF;
    IF EXISTS(SELECT 1 FROM bridge_receipt r WHERE r.fence=p_fence)
    THEN status:='conflict'; RETURN NEXT; RETURN; END IF;
    IF (SELECT count(*) FROM bridge_receipt)>=4096
    THEN status:='full'; RETURN NEXT; RETURN; END IF;
    IF EXISTS(SELECT 1 FROM work_task w WHERE w.member_id=member
              AND w.idempotency_key='bridge:'||p_question::text)
    THEN RAISE EXCEPTION 'missing bridge receipt'; END IF;
    -- Match the existing shared Python admission policy and quotas.
    -- Serialize on the same scheduler row; count all admitted attempts.
    WITH expired AS (
        UPDATE work_task SET state='expired'
          WHERE state='queued' AND deadline<=t RETURNING id
    ) INSERT INTO task_outcome SELECT id,'expired','deadline elapsed',t,0 FROM expired;
    IF ctl.rest_enabled THEN
        local_time:=to_timestamp(t) AT TIME ZONE 'America/New_York';
        IF extract(year FROM local_time) NOT BETWEEN 2000 AND 2099
           OR extract(hour FROM local_time)<8
        THEN status:='resting'; RETURN NEXT; RETURN; END IF;
    END IF;
    SELECT e.tier INTO tier FROM scheduler_entitlement e
      WHERE e.member_id=member AND e.valid_until>t;
    tier:=coalesce(tier,0);
    IF EXISTS(SELECT 1 FROM work_task w WHERE w.state IN ('queued','running')
              AND w.submitted_at>t)
    THEN status:='invalid'; RETURN NEXT; RETURN; END IF;
    IF (SELECT count(*) FROM work_task w WHERE w.state='queued')>=10 OR
       (SELECT count(*) FROM work_task w WHERE w.state='queued'
        AND (CASE WHEN tier=0 THEN w.tier_snapshot=0 ELSE w.tier_snapshot>0 END))
          >=(CASE WHEN tier=0 THEN 3 ELSE 5 END)
    THEN status:='full'; RETURN NEXT; RETURN; END IF;
    IF (SELECT count(*) FROM work_task w WHERE w.member_id=member
        AND w.state IN ('queued','running'))>=(CASE WHEN tier<=2 THEN 1 WHEN tier<=4 THEN 2 ELSE 3 END)
    THEN status:='member_limit'; RETURN NEXT; RETURN; END IF;
    SELECT count(*) FILTER (WHERE w.submitted_at>t-3600),count(*) INTO hourly,daily
      FROM work_task w WHERE w.member_id=member AND w.submitted_at>t-86400;
    IF hourly>=(CASE WHEN tier=0 THEN 3 ELSE 10 END) OR daily>=(CASE WHEN tier=0 THEN 10 ELSE 30 END)
    THEN status:='member_quota'; RETURN NEXT; RETURN; END IF;
    SELECT count(*) FILTER (WHERE w.submitted_at>t-3600),count(*) INTO hourly,daily
      FROM work_task w WHERE w.member_id IS NOT NULL AND w.submitted_at>t-86400;
    IF hourly>=20 OR daily>=120
    THEN status:='community_quota'; RETURN NEXT; RETURN; END IF;
    task_id:=gen_random_uuid();
    INSERT INTO work_task(id,member_id,tier_snapshot,idempotency_key,payload,submitted_at,deadline,state)
      VALUES(task_id,member,tier,'bridge:'||p_question::text,p_text,t,p_expiry-5,'queued');
    INSERT INTO bridge_receipt(question_id,cloud_owner,local_member,fence,task_id,payload_sha256,expires_at,admitted_at)
      VALUES(p_question,p_owner,member,p_fence,task_id,digest,p_expiry,t);
    status:='accept'; RETURN NEXT;
END;
$admit$;

CREATE FUNCTION penny_bridge_ack(p_question uuid,p_fence uuid,p_task uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $ack$
DECLARE t bigint; r record;
BEGIN
    PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    SELECT b.acked_at INTO r FROM bridge_receipt b JOIN bridge_member m
      ON m.cloud_owner=b.cloud_owner AND m.local_member=b.local_member AND m.enabled
      WHERE b.question_id=p_question AND b.fence=p_fence AND b.task_id=p_task
        AND b.expires_at>t AND b.remote_rejected_at IS NULL
      FOR UPDATE OF b,m;
    IF NOT FOUND THEN RETURN false; END IF;
    IF r.acked_at IS NULL THEN
        UPDATE bridge_receipt SET acked_at=t WHERE question_id=p_question;
    END IF;
    RETURN true;
END;
$ack$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_bridge_admit(uuid,uuid,uuid,bigint,text)',
        'penny_bridge_ack(uuid,uuid,uuid)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
