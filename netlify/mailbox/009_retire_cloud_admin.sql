BEGIN;
-- Maker directive: no cloud administration API or runtime admin grants.
-- Preserve historical audit rows. Disable former identities and retire the
-- callable functions (which also removes their existing EXECUTE grants).
UPDATE mailbox_admin SET enabled=false;
DROP FUNCTION mailbox_admin_status(uuid);
DROP FUNCTION mailbox_admin_pause(uuid);
DROP FUNCTION mailbox_admin_allow(uuid,text);
DO $retire$
DECLARE ns name:=current_schema();
BEGIN
    IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
    EXECUTE format('REVOKE ALL ON TABLE %I.mailbox_admin,%I.mailbox_admin_event,%I.mailbox_admin_budget FROM PUBLIC',ns,ns,ns);
END;
$retire$;
COMMIT;
