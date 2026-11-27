BEGIN;
-- Ordinary completion only. Specialized intake must retain its existing
-- atomic validators until individually scoped; no implicit promotion.
CREATE FUNCTION penny_inference_complete_draft(p_cycle uuid,p_task uuid,p_fence uuid,p_result text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $complete$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate inference_runtime%ROWTYPE;
    task work_task%ROWTYPE;
    snap record;
    t bigint;
    final_state text:='succeeded';
    final_text text:=p_result;
BEGIN
    IF p_result IS NULL OR length(p_result) NOT BETWEEN 1 AND 16000
       OR p_result !~ '[^[:space:]]' THEN RETURN 'refused'; END IF;
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN 'refused'; END IF;
    SELECT * INTO gate FROM inference_runtime WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.uncertain OR p_cycle IS NULL
       OR gate.cycle_token IS DISTINCT FROM p_cycle
       OR gate.claim_cycle_token IS DISTINCT FROM p_cycle
    THEN RETURN 'refused'; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    SELECT w.* INTO task FROM work_task w WHERE w.id=p_task
      AND w.fence=p_fence AND w.state='running' AND w.lease_until>t FOR UPDATE;
    IF NOT FOUND THEN RETURN 'refused'; END IF;
    -- These are the existing specialized intake routes, never inferred
    -- from model text. The trusted legacy adapter handles them atomically.
    IF task.member_id IS NULL AND (
        starts_with(task.idempotency_key,'memory-review:') OR
        starts_with(task.idempotency_key,'memory-informed:maintenance-') OR
        starts_with(task.idempotency_key,'business-draft:') OR
        starts_with(task.idempotency_key,'workshop:'))
    THEN RETURN 'specialized'; END IF;
    -- Recheck current consent and snapshot IDs under the same lock used by
    -- member preference deletion and withdrawal. Do not retain stale text.
    SELECT p.fence,p.preference_ids,s.member_id,s.epoch INTO snap
      FROM member_recall_snapshot p JOIN member_recall_scope s ON s.task_id=p.task_id
      WHERE p.task_id=task.id;
    IF FOUND THEN
        IF snap.fence IS DISTINCT FROM task.fence OR
           snap.member_id IS DISTINCT FROM task.member_id OR
           NOT EXISTS(SELECT 1 FROM member_memory_consent c
              WHERE c.member_id=snap.member_id AND c.epoch=snap.epoch
              AND c.enabled AND c.policy_version='member-memory-v1' AND c.expires_at>t)
           OR EXISTS(SELECT 1 FROM unnest(snap.preference_ids) AS i(id)
              WHERE NOT EXISTS(SELECT 1 FROM member_memory m
                WHERE m.member_id=snap.member_id AND m.epoch=snap.epoch AND m.id=i.id))
        THEN
            final_state:='canceled';
            final_text:='personal memory permission changed';
        END IF;
    END IF;
    UPDATE work_task SET state=final_state WHERE id=task.id;
    INSERT INTO task_outcome(task_id,status,result,finished_at,compute_seconds)
      VALUES(task.id,final_state,final_text,t,
             greatest(1,least(t,task.lease_until)-task.started_at));
    UPDATE scheduler_control SET last_member_id=task.member_id WHERE singleton;
    RETURN CASE WHEN final_state='succeeded' THEN 'completed' ELSE 'canceled' END;
END;
$complete$;

DO $secure$
DECLARE ns name:=current_schema();
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    EXECUTE format('ALTER FUNCTION %I.penny_inference_complete_draft(uuid,uuid,uuid,text) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_inference_complete_draft(uuid,uuid,uuid,text) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
