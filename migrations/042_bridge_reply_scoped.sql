BEGIN;
-- Only the trusted owner can use the internal helper. Worker entrypoints
-- return reviewed content or record a fenced receipt; never approve a draft.
CREATE FUNCTION penny_bridge_reviewed(p_question uuid)
RETURNS TABLE(fence uuid,draft_sha256 text,result text,delivered_at bigint)
LANGUAGE plpgsql AS $reviewed$
DECLARE t_now bigint;
BEGIN
    t_now:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    RETURN QUERY SELECT r.fence,a.draft_sha256,o.result,a.delivered_at
      FROM bridge_receipt r
      JOIN bridge_member m ON m.cloud_owner=r.cloud_owner
          AND m.local_member=r.local_member AND m.enabled
      JOIN work_task t ON t.id=r.task_id AND t.member_id=r.local_member
          AND t.state='succeeded'
      JOIN task_outcome o ON o.task_id=t.id AND o.status='succeeded'
      JOIN bridge_release a ON a.question_id=r.question_id
      WHERE r.question_id=p_question AND r.acked_at IS NOT NULL
        AND r.expires_at>t_now AND r.remote_rejected_at IS NULL
        AND a.identity_sha256='e1ef18151ddd473f2d73756204740a97e28c5cd254c0b46a500196f069a08e9a'
        AND a.draft_sha256=encode(sha256(convert_to(o.result,'UTF8')),'hex')
        AND length(o.result) BETWEEN 1 AND 16000
        AND o.result ~ '[^[:space:]]'
      FOR UPDATE OF r,m,t,o,a;
END;
$reviewed$;

CREATE FUNCTION penny_bridge_pending_reply(p_question uuid)
RETURNS TABLE(fence uuid,draft_sha256 text,result text)
LANGUAGE plpgsql SECURITY DEFINER AS $pending$
DECLARE p boolean;
BEGIN
    SELECT c.paused INTO p FROM scheduler_control c WHERE c.singleton FOR UPDATE;
    IF NOT FOUND OR p THEN RETURN; END IF;
    RETURN QUERY SELECT r.fence,r.draft_sha256,r.result
      FROM penny_bridge_reviewed(p_question) r WHERE r.delivered_at IS NULL;
END;
$pending$;

CREATE FUNCTION penny_bridge_record_delivery(p_question uuid,p_fence uuid,p_digest text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $delivery$
DECLARE r record;
BEGIN
    PERFORM 1 FROM scheduler_control c WHERE c.singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    -- Allow recording an already completed external effect during pause,
    -- but never change approval, digest, owner, fence or reviewed text.
    SELECT * INTO r FROM penny_bridge_reviewed(p_question);
    IF NOT FOUND OR r.fence IS DISTINCT FROM p_fence OR
       r.draft_sha256 IS DISTINCT FROM p_digest THEN RETURN false; END IF;
    IF r.delivered_at IS NULL THEN
        UPDATE bridge_release SET delivered_at=floor(extract(epoch FROM clock_timestamp()))::bigint
          WHERE question_id=p_question AND delivered_at IS NULL;
    END IF;
    RETURN true;
END;
$delivery$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_bridge_reviewed(uuid)',
        'penny_bridge_pending_reply(uuid)','penny_bridge_record_delivery(uuid,uuid,text)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
