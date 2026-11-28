BEGIN;
-- One claim attempt per reserved inference cycle. This is not a second queue.
ALTER TABLE inference_runtime ADD COLUMN claim_cycle_token uuid;

CREATE FUNCTION penny_inference_claim(p_cycle uuid)
RETURNS TABLE(task_id uuid,fence uuid,payload text,lease_until bigint,
              memory_enabled boolean,personal_memory_enabled boolean)
LANGUAGE plpgsql SECURITY DEFINER AS $claim$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate inference_runtime%ROWTYPE;
    chosen work_task%ROWTYPE;
    t bigint;
    new_fence uuid;
    new_lease bigint;
BEGIN
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'scheduler unavailable'; END IF;
    SELECT * INTO gate FROM inference_runtime WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.uncertain OR p_cycle IS NULL OR
       gate.cycle_token IS DISTINCT FROM p_cycle OR
       gate.claim_cycle_token IS NOT DISTINCT FROM p_cycle
    THEN RAISE EXCEPTION 'invalid or consumed inference cycle'; END IF;
    -- Consume even an empty claim attempt, preventing arbitrary queue browsing.
    UPDATE inference_runtime SET claim_cycle_token=p_cycle WHERE singleton;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    IF ctl.paused OR NOT gate.enabled OR
       penny_bridge_rest_closed(ctl.rest_enabled,t) THEN RETURN; END IF;
    IF EXISTS(SELECT 1 FROM work_task w WHERE w.state='running')
    THEN RAISE EXCEPTION 'active inference task'; END IF;
    WITH expired AS (
        UPDATE work_task SET state='expired' WHERE state='queued' AND deadline<=t
          RETURNING id
    ) INSERT INTO task_outcome SELECT id,'expired','deadline elapsed',t,0 FROM expired;
    -- Entitlement changes cancel queued tasks rather than moving them into
    -- a class with different capacity or permissions.
    WITH changed AS (
        UPDATE work_task w SET state='canceled'
          WHERE w.state='queued' AND w.member_id IS NOT NULL
          AND w.tier_snapshot IS DISTINCT FROM coalesce(
            (SELECT e.tier FROM scheduler_entitlement e
             WHERE e.member_id=w.member_id AND e.valid_until>t),0)
          RETURNING w.id
    ) INSERT INTO task_outcome SELECT id,'canceled','entitlement changed',t,0 FROM changed;
    IF EXISTS(SELECT 1 FROM work_task w WHERE w.state='queued'
              AND (w.submitted_at<0 OR w.submitted_at>t))
    THEN RAISE EXCEPTION 'invalid queue clock'; END IF;
    -- Exact scheduler policy: oldest aged task first; otherwise avoid the
    -- last member when possible, then minimize measured usage / target share.
    -- Integer multipliers 1/2/6 preserve the 60/30/10 ratios exactly.
    WITH usage AS (
        SELECT coalesce(sum(o.compute_seconds) FILTER (WHERE w.member_id IS NULL),0)::numeric AS business,
               coalesce(sum(o.compute_seconds) FILTER (WHERE w.tier_snapshot>0),0)::numeric AS supporter,
               coalesce(sum(o.compute_seconds) FILTER (WHERE w.tier_snapshot=0),0)::numeric AS free
        FROM task_outcome o JOIN work_task w ON w.id=o.task_id
        WHERE o.finished_at>t-86400
    ), candidates AS (
        SELECT w.*,w.submitted_at<=t-900 AS aged,
               CASE WHEN w.member_id IS NULL THEN 60
                    WHEN w.tier_snapshot>0 THEN 30 ELSE 10 END AS share,
               CASE WHEN w.member_id IS NULL THEN u.business
                    WHEN w.tier_snapshot>0 THEN u.supporter*2 ELSE u.free*6 END AS score
        FROM work_task w CROSS JOIN usage u WHERE w.state='queued' AND w.deadline>t
    ), eligible AS (
        SELECT c.* FROM candidates c WHERE
            CASE WHEN EXISTS(SELECT 1 FROM candidates a WHERE a.aged)
                 THEN c.aged
                 WHEN ctl.last_member_id IS NOT NULL AND EXISTS(
                      SELECT 1 FROM candidates a WHERE a.member_id IS DISTINCT FROM ctl.last_member_id)
                 THEN c.member_id IS DISTINCT FROM ctl.last_member_id
                 ELSE true END
    )
    SELECT w.* INTO chosen FROM eligible e JOIN work_task w ON w.id=e.id
      ORDER BY CASE WHEN e.aged THEN 0 ELSE e.score END,
               CASE WHEN e.aged THEN 0 ELSE -e.share END,
               CASE WHEN e.aged THEN 0 ELSE -coalesce(e.tier_snapshot,0) END,
               e.submitted_at,e.id LIMIT 1;
    IF NOT FOUND THEN RETURN; END IF;
    new_fence:=gen_random_uuid();
    new_lease:=least(chosen.deadline,t+CASE WHEN chosen.member_id IS NULL THEN 900 ELSE 120 END);
    UPDATE work_task w SET state='running',fence=new_fence,started_at=t,lease_until=new_lease
      WHERE w.id=chosen.id AND w.state='queued';
    IF NOT FOUND THEN RAISE EXCEPTION 'claim disappeared'; END IF;
    task_id:=chosen.id; fence:=new_fence; payload:=chosen.payload; lease_until:=new_lease;
    memory_enabled:=chosen.member_id IS NULL AND starts_with(chosen.idempotency_key,'memory-informed:');
    personal_memory_enabled:=chosen.member_id IS NOT NULL AND EXISTS(
        SELECT 1 FROM member_recall_scope s WHERE s.task_id=chosen.id AND s.member_id=chosen.member_id);
    RETURN NEXT;
END;
$claim$;

DO $secure$
DECLARE ns name:=current_schema();
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    EXECUTE format('ALTER FUNCTION %I.penny_inference_claim(uuid) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_inference_claim(uuid) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
