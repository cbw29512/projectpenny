BEGIN;
-- Never reclaim expired claims automatically. Ambiguous transfers are
-- terminal at this layer until a future reconciliation protocol exists.
CREATE FUNCTION mailbox_claim()
RETURNS TABLE(question_id uuid,owner_id uuid,body text,fence uuid,lease_until timestamptz)
LANGUAGE plpgsql AS $claim_body$
DECLARE gate boolean; at_time timestamptz; picked uuid;
BEGIN
    SELECT enabled INTO gate FROM mailbox_control WHERE singleton FOR UPDATE;
    IF gate IS DISTINCT FROM true THEN RETURN; END IF;
    at_time := clock_timestamp();
    PERFORM mailbox_expire(at_time);
    -- Initially one bridge transfer at a time, independent of local scheduler.
    IF EXISTS(SELECT 1 FROM mailbox_question WHERE state IN ('claimed','locally_accepted')) THEN RETURN; END IF;
    SELECT q.id INTO picked FROM mailbox_question q JOIN mailbox_member m ON m.id=q.owner_id
    WHERE q.state='submitted' AND m.enabled ORDER BY q.submitted_at,q.id LIMIT 1;
    IF picked IS NULL THEN RETURN; END IF;
    RETURN QUERY UPDATE mailbox_question q SET state='claimed',fence=gen_random_uuid(),
       lease_until=least(q.expires_at,at_time+interval '15 minutes')
       WHERE q.id=picked RETURNING q.id,q.owner_id,q.body,q.fence,q.lease_until;
END;
$claim_body$;

CREATE FUNCTION mailbox_ack(p_id uuid,p_fence uuid,p_local uuid)
RETURNS boolean LANGUAGE plpgsql AS $ack_body$
DECLARE at_time timestamptz; q mailbox_question%ROWTYPE;
BEGIN
    PERFORM 1 FROM mailbox_control WHERE singleton FOR UPDATE;
    at_time := clock_timestamp();
    PERFORM mailbox_expire(at_time);
    SELECT * INTO q FROM mailbox_question WHERE id=p_id AND fence=p_fence;
    IF NOT FOUND OR p_local IS NULL OR p_local='00000000-0000-0000-0000-000000000000' THEN RETURN false; END IF;
    IF NOT EXISTS(SELECT 1 FROM mailbox_member WHERE id=q.owner_id AND enabled) THEN RETURN false; END IF;
    IF q.state IN ('locally_accepted','answered') THEN RETURN q.local_task_id=p_local; END IF;
    IF q.state<>'claimed' OR q.lease_until<=at_time OR q.expires_at<=at_time THEN RETURN false; END IF;
    UPDATE mailbox_question SET state='locally_accepted',local_task_id=p_local WHERE id=p_id;
    RETURN true;
END;
$ack_body$;

CREATE FUNCTION mailbox_answer(p_id uuid,p_fence uuid,p_answer text)
RETURNS boolean LANGUAGE plpgsql AS $answer_body$
DECLARE at_time timestamptz; q mailbox_question%ROWTYPE;
BEGIN
    IF p_answer IS NULL OR length(btrim(p_answer))=0 OR length(p_answer)>16000
       OR octet_length(p_answer)>64000 OR p_answer !~ '[^[:space:]]' THEN RETURN false; END IF;
    PERFORM 1 FROM mailbox_control WHERE singleton FOR UPDATE;
    at_time := clock_timestamp();
    PERFORM mailbox_expire(at_time);
    SELECT * INTO q FROM mailbox_question WHERE id=p_id AND fence=p_fence;
    IF NOT FOUND THEN RETURN false; END IF;
    IF NOT EXISTS(SELECT 1 FROM mailbox_member WHERE id=q.owner_id AND enabled) THEN RETURN false; END IF;
    IF q.state='answered' THEN RETURN q.answer=p_answer; END IF;
    IF q.state<>'locally_accepted' OR q.lease_until<=at_time OR q.expires_at<=at_time THEN RETURN false; END IF;
    UPDATE mailbox_question SET state='answered',answer=p_answer WHERE id=p_id;
    RETURN true;
END;
$answer_body$;

CREATE FUNCTION mailbox_reject(p_id uuid,p_fence uuid)
RETURNS boolean LANGUAGE plpgsql AS $reject_body$
DECLARE q mailbox_question%ROWTYPE;
BEGIN
    PERFORM 1 FROM mailbox_control WHERE singleton FOR UPDATE;
    PERFORM mailbox_expire(clock_timestamp());
    SELECT * INTO q FROM mailbox_question WHERE id=p_id AND fence=p_fence;
    IF NOT FOUND THEN RETURN false; END IF;
    IF q.state='rejected' THEN RETURN true; END IF;
    IF q.state NOT IN ('claimed','locally_accepted') THEN RETURN false; END IF;
    UPDATE mailbox_question SET state='rejected' WHERE id=p_id;
    RETURN true;
END;
$reject_body$;

-- Trusted maintenance only. Keep quota history for longer than 24h.
CREATE FUNCTION mailbox_purge() RETURNS integer LANGUAGE plpgsql AS $purge_body$
DECLARE removed integer;
BEGIN
    PERFORM 1 FROM mailbox_control WHERE singleton FOR UPDATE;
    PERFORM mailbox_expire(clock_timestamp());
    DELETE FROM mailbox_question WHERE id IN (
      SELECT id FROM mailbox_question WHERE state IN ('answered','rejected','expired')
        AND submitted_at<=clock_timestamp()-interval '48 hours'
      ORDER BY submitted_at,id LIMIT 50);
    GET DIAGNOSTICS removed = ROW_COUNT;
    RETURN removed;
END;
$purge_body$;
-- No default PUBLIC execution grant. Functions are not HTTP routes.
REVOKE EXECUTE ON FUNCTION mailbox_expire(timestamptz),
  mailbox_submit(uuid,uuid,text),mailbox_read(uuid,uuid),mailbox_claim(),
  mailbox_ack(uuid,uuid,uuid),mailbox_answer(uuid,uuid,text),
  mailbox_reject(uuid,uuid),mailbox_purge() FROM PUBLIC;
COMMIT;
