BEGIN;
-- Install under a dedicated, trusted mailbox schema owner. Runtime callers
-- must not own this schema or be able to create objects in it.
DO $secure$
DECLARE
    ns name := current_schema();
    signature text;
BEGIN
    IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema')
       OR ns LIKE 'pg_temp_%' THEN
        RAISE EXCEPTION 'dedicated mailbox schema required';
    END IF;
    EXECUTE format('REVOKE ALL ON SCHEMA %I FROM PUBLIC',ns);
    EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA %I FROM PUBLIC',ns);
    -- Pin resolution of every mailbox relation and routine; temp objects
    -- must never shadow trusted tables. Only the trusted owner may CREATE.
    FOREACH signature IN ARRAY ARRAY[
        'mailbox_expire(timestamptz)','mailbox_submit(uuid,uuid,text)',
        'mailbox_read(uuid,uuid)','mailbox_claim()',
        'mailbox_ack(uuid,uuid,uuid)','mailbox_answer(uuid,uuid,text)',
        'mailbox_reject(uuid,uuid)','mailbox_purge()'
    ] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',
                       ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
        IF signature <> 'mailbox_expire(timestamptz)' THEN
            EXECUTE format('ALTER FUNCTION %I.%s SECURITY DEFINER',ns,signature);
        END IF;
    END LOOP;
END;
$secure$;
COMMIT;
