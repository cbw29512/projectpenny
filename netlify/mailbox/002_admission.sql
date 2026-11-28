BEGIN;
-- SECURITY INVOKER by default. These are server-only routines; deployment
-- role grants and trusted identity resolution must be implemented separately.
CREATE FUNCTION mailbox_expire(p_now timestamptz) RETURNS void
LANGUAGE sql AS $expire_body$
    UPDATE mailbox_question SET state='expired'
    WHERE state IN ('submitted','claimed','locally_accepted')
      AND (expires_at<=p_now OR (lease_until IS NOT NULL AND lease_until<=p_now));
$expire_body$;

CREATE FUNCTION mailbox_submit(p_owner uuid,p_key uuid,p_body text)
RETURNS TABLE(status text,question_id uuid,replayed boolean)
LANGUAGE plpgsql AS $submit_body$
DECLARE
    gate boolean;
    at_time timestamptz;
    old_row mailbox_question%ROWTYPE;
    new_id uuid;
BEGIN
    IF p_owner IS NULL OR p_key IS NULL OR p_body IS NULL
       OR p_owner='00000000-0000-0000-0000-000000000000'
       OR p_key='00000000-0000-0000-0000-000000000000'
       OR length(btrim(p_body))=0 OR length(p_body)>2000 OR octet_length(p_body)>8000
       OR p_body !~ '[^[:space:]]' THEN
        RETURN QUERY SELECT 'invalid'::text,NULL::uuid,false; RETURN;
    END IF;
    SELECT enabled INTO gate FROM mailbox_control WHERE singleton FOR UPDATE;
    at_time := clock_timestamp();
    IF NOT EXISTS(SELECT 1 FROM mailbox_member WHERE id=p_owner AND enabled) THEN
        RETURN QUERY SELECT 'denied'::text,NULL::uuid,false; RETURN;
    END IF;
    PERFORM mailbox_expire(at_time);
    SELECT * INTO old_row FROM mailbox_question WHERE owner_id=p_owner AND request_key=p_key;
    IF FOUND THEN
        IF old_row.body<>p_body THEN
            RETURN QUERY SELECT 'conflict'::text,NULL::uuid,false;
        ELSE
            RETURN QUERY SELECT 'accepted'::text,old_row.id,true;
        END IF;
        RETURN;
    END IF;
    IF gate IS DISTINCT FROM true THEN
        RETURN QUERY SELECT 'paused'::text,NULL::uuid,false; RETURN;
    END IF;
    -- Count every accepted request, not just successful replies. No tier trust.
    IF (SELECT count(*) FROM mailbox_question WHERE owner_id=p_owner AND submitted_at>at_time-interval '1 hour')>=3
       OR (SELECT count(*) FROM mailbox_question WHERE owner_id=p_owner AND submitted_at>at_time-interval '24 hours')>=10 THEN
        RETURN QUERY SELECT 'member_quota'::text,NULL::uuid,false; RETURN;
    END IF;
    IF (SELECT count(*) FROM mailbox_question WHERE submitted_at>at_time-interval '1 hour')>=20
       OR (SELECT count(*) FROM mailbox_question WHERE submitted_at>at_time-interval '24 hours')>=120 THEN
        RETURN QUERY SELECT 'community_quota'::text,NULL::uuid,false; RETURN;
    END IF;
    IF EXISTS(SELECT 1 FROM mailbox_question WHERE owner_id=p_owner AND state IN ('submitted','claimed','locally_accepted')) THEN
        RETURN QUERY SELECT 'member_busy'::text,NULL::uuid,false; RETURN;
    END IF;
    IF (SELECT count(*) FROM mailbox_question WHERE state IN ('submitted','claimed','locally_accepted'))>=8
       OR (SELECT count(*) FROM mailbox_question)>=512 THEN
        RETURN QUERY SELECT 'full'::text,NULL::uuid,false; RETURN;
    END IF;
    new_id := gen_random_uuid();
    INSERT INTO mailbox_question(id,owner_id,request_key,body,submitted_at,expires_at,state)
    VALUES(new_id,p_owner,p_key,p_body,at_time,at_time+interval '1 hour','submitted');
    RETURN QUERY SELECT 'accepted'::text,new_id,false;
END;
$submit_body$;

-- Read only the exact owner's question. Expired data is not delivered.
CREATE FUNCTION mailbox_read(p_owner uuid,p_id uuid)
RETURNS TABLE(question_id uuid,status text,reply text)
LANGUAGE sql AS $read_body$
    SELECT q.id,
        CASE WHEN q.state IN ('submitted','claimed','locally_accepted')
          AND (q.expires_at<=statement_timestamp() OR q.lease_until<=statement_timestamp())
          THEN 'expired' ELSE q.state END,
        CASE WHEN q.state='answered' THEN q.answer ELSE NULL END
    FROM mailbox_question q JOIN mailbox_member m ON m.id=q.owner_id AND m.enabled
    WHERE q.id=p_id AND q.owner_id=p_owner
      AND q.submitted_at>statement_timestamp()-interval '48 hours';
$read_body$;
COMMIT;
