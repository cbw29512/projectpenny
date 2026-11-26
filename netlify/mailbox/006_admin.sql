BEGIN;
-- Independent allowlist: ordinary membership grants no administration.
CREATE TABLE mailbox_admin (
    id uuid PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE mailbox_admin_event (
    id uuid PRIMARY KEY,
    admin_id uuid NOT NULL REFERENCES mailbox_admin(id),
    action text NOT NULL CHECK(action='pause_admission'),
    recorded_at timestamptz NOT NULL
);
CREATE FUNCTION mailbox_admin_status(p_admin uuid)
RETURNS TABLE(admission_open boolean,pending bigint,processing bigint)
LANGUAGE plpgsql SECURITY DEFINER AS $status_body$
BEGIN
    IF NOT EXISTS(SELECT 1 FROM mailbox_admin WHERE id=p_admin AND enabled)
    THEN RETURN; END IF;
    RETURN QUERY SELECT c.enabled,
        (SELECT count(*) FROM mailbox_question q WHERE q.state='submitted'
          AND q.expires_at>statement_timestamp()),
        (SELECT count(*) FROM mailbox_question q WHERE q.state IN ('claimed','locally_accepted')
          AND q.expires_at>statement_timestamp() AND q.lease_until>statement_timestamp())
    FROM mailbox_control c WHERE c.singleton;
END;
$status_body$;

CREATE FUNCTION mailbox_admin_pause(p_admin uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $pause_body$
DECLARE was_open boolean;
BEGIN
    SELECT enabled INTO was_open FROM mailbox_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    PERFORM 1 FROM mailbox_admin WHERE id=p_admin AND enabled FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    IF was_open THEN
        UPDATE mailbox_control SET enabled=false WHERE singleton;
        INSERT INTO mailbox_admin_event VALUES
          (gen_random_uuid(),p_admin,'pause_admission',clock_timestamp());
    END IF;
    -- A repeated pause never reopens or creates an unlimited audit stream.
    RETURN true;
END;
$pause_body$;

DO $secure_admin$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
    EXECUTE format('REVOKE ALL ON TABLE %I.mailbox_admin,%I.mailbox_admin_event FROM PUBLIC',ns,ns);
    FOREACH signature IN ARRAY ARRAY['mailbox_admin_status(uuid)','mailbox_admin_pause(uuid)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure_admin$;
COMMIT;
