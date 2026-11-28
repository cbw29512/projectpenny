BEGIN;
-- Record one recall attempt even when consent is absent or no preferences exist.
-- No preference text is retained by this marker.
CREATE TABLE inference_personal_recall_attempt (
    task_id uuid PRIMARY KEY REFERENCES work_task(id),
    fence uuid NOT NULL,
    recorded_at bigint NOT NULL
);
REVOKE ALL ON inference_personal_recall_attempt FROM PUBLIC;

CREATE FUNCTION penny_inference_personal_recall(p_cycle uuid,p_task uuid,p_fence uuid)
RETURNS TABLE(id uuid,preference text)
LANGUAGE plpgsql SECURITY DEFINER AS $recall$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate inference_runtime%ROWTYPE;
    scope member_recall_scope%ROWTYPE;
    t bigint;
    ids uuid[];
BEGIN
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'scheduler unavailable'; END IF;
    SELECT * INTO gate FROM inference_runtime WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.uncertain OR p_cycle IS NULL OR
       gate.cycle_token IS DISTINCT FROM p_cycle OR
       gate.claim_cycle_token IS DISTINCT FROM p_cycle
    THEN RAISE EXCEPTION 'invalid inference cycle'; END IF;
    IF ctl.paused OR NOT gate.enabled THEN RETURN; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    SELECT s.* INTO scope FROM member_recall_scope s
      JOIN work_task w ON w.id=s.task_id AND w.member_id=s.member_id
      WHERE w.id=p_task AND w.fence=p_fence AND w.state='running'
        AND w.lease_until>t AND w.member_id IS NOT NULL;
    IF NOT FOUND THEN RETURN; END IF;
    IF EXISTS(SELECT 1 FROM member_recall_snapshot s WHERE s.task_id=p_task)
       OR EXISTS(SELECT 1 FROM inference_personal_recall_attempt a WHERE a.task_id=p_task)
    THEN RAISE EXCEPTION 'personal recall already performed'; END IF;
    INSERT INTO inference_personal_recall_attempt VALUES(p_task,p_fence,t);
    IF NOT EXISTS(SELECT 1 FROM member_memory_consent c
        WHERE c.member_id=scope.member_id AND c.epoch=scope.epoch
          AND c.enabled AND c.policy_version='member-memory-v1' AND c.expires_at>t)
    THEN RETURN; END IF;
    -- Snapshot IDs only, before returning any content. Same scheduler lock
    -- as preference deletion, withdrawal and completion.
    SELECT array_agg(m.id ORDER BY m.created_at DESC,m.id) INTO ids
    FROM (SELECT p.id,p.created_at FROM member_memory p
          WHERE p.member_id=scope.member_id AND p.epoch=scope.epoch
          ORDER BY p.created_at DESC,p.id LIMIT 3) m;
    IF ids IS NULL THEN RETURN; END IF;
    INSERT INTO member_recall_snapshot VALUES(p_task,p_fence,ids,t);
    RETURN QUERY SELECT m.id,m.preference FROM member_memory m
      WHERE m.member_id=scope.member_id AND m.epoch=scope.epoch AND m.id=ANY(ids)
      ORDER BY m.created_at DESC,m.id;
END;
$recall$;

DO $secure$
DECLARE ns name:=current_schema();
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    EXECUTE format('ALTER FUNCTION %I.penny_inference_personal_recall(uuid,uuid,uuid) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_inference_personal_recall(uuid,uuid,uuid) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
