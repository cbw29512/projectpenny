BEGIN;
-- Parse JSON (not jsonb): preserve duplicate keys for rejection.
-- Invalid output is still a completed draft, but never a learning candidate.
CREATE FUNCTION penny_private_parse_learning(p_raw text)
RETURNS TABLE(kind text,content text)
LANGUAGE plpgsql AS $learning$
DECLARE
    parsed json;
    k text;
    c text;
    -- Python str.strip whitespace set, excluding NUL (not representable).
    whitespace constant text:=U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000';
BEGIN
    IF p_raw IS NULL OR length(p_raw)>8000 THEN RETURN; END IF;
    parsed:=p_raw::json;
    IF json_typeof(parsed) IS DISTINCT FROM 'object' THEN RETURN; END IF;
    IF (SELECT count(*) FROM json_each(parsed))<>2 OR
       (SELECT count(DISTINCT e.key) FROM json_each(parsed) e)<>2 OR
       json_typeof(parsed->'kind') IS DISTINCT FROM 'string' OR
       json_typeof(parsed->'content') IS DISTINCT FROM 'string'
    THEN RETURN; END IF;
    k:=parsed->>'kind';
    c:=btrim(parsed->>'content',whitespace);
    IF k NOT IN ('lesson','failure','idea','skill','milestone') OR
       c IS NULL OR length(c) NOT BETWEEN 1 AND 1000
    THEN RETURN; END IF;
    kind:=k; content:=c; RETURN NEXT;
EXCEPTION WHEN data_exception THEN
    -- Malformed JSON or invalid Unicode is not a trusted candidate.
    RETURN;
END;
$learning$;

CREATE OR REPLACE FUNCTION penny_inference_complete_draft(p_cycle uuid,p_task uuid,p_fence uuid,p_result text)
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
    IF final_state='succeeded' AND task.member_id IS NULL
       AND starts_with(task.idempotency_key,'memory-review:') THEN
        -- Only the stored task route can stage learning. Never accept model
        -- claims of approval, evidence, identity or policy authority.
        INSERT INTO memory_candidate(source_task_id,kind,content)
          SELECT task.id,c.kind,c.content FROM penny_private_parse_learning(p_result) c;
    END IF;
    RETURN CASE WHEN final_state='succeeded' THEN 'completed' ELSE 'canceled' END;
END;
$complete$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_private_parse_learning(text)',
        'penny_inference_complete_draft(uuid,uuid,uuid,text)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
