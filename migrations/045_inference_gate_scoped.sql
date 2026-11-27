BEGIN;
-- Existing uncertain rows remain uncertain and require operator recovery.
ALTER TABLE inference_runtime ADD COLUMN cycle_token uuid;
CREATE FUNCTION penny_inference_begin()
RETURNS TABLE(status text,token uuid)
LANGUAGE plpgsql SECURITY DEFINER AS $begin$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate inference_runtime%ROWTYPE;
    t bigint;
BEGIN
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR ctl.paused THEN status:='paused'; RETURN NEXT; RETURN; END IF;
    SELECT * INTO gate FROM inference_runtime WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.enabled THEN status:='paused'; RETURN NEXT; RETURN; END IF;
    IF gate.uncertain OR gate.cycle_token IS NOT NULL THEN
        status:='blocked'; RETURN NEXT; RETURN;
    END IF;
    IF EXISTS(SELECT 1 FROM work_task WHERE state='running') THEN
        UPDATE inference_runtime SET uncertain=true,last_result='interrupted' WHERE singleton;
        status:='blocked'; RETURN NEXT; RETURN;
    END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    IF penny_bridge_rest_closed(ctl.rest_enabled,t) THEN
        status:='paused'; RETURN NEXT; RETURN;
    END IF;
    token:=gen_random_uuid();
    UPDATE inference_runtime SET uncertain=true,cycle_token=token,
        last_started=t,last_result='interrupted' WHERE singleton;
    status:='reserved'; RETURN NEXT;
END;
$begin$;

CREATE FUNCTION penny_inference_finish(p_token uuid,p_result text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $finish$
DECLARE
    gate inference_runtime%ROWTYPE;
    safe boolean;
    t bigint;
BEGIN
    PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN 'blocked'; END IF;
    SELECT * INTO gate FROM inference_runtime WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.uncertain OR p_token IS NULL
       OR gate.cycle_token IS DISTINCT FROM p_token
    THEN RETURN 'blocked'; END IF;
    -- Consume the cycle token once, even on failure. Only the trusted Maker
    -- may recover a sticky uncertain state after investigating the process.
    safe:=coalesce(p_result IN ('idle','completed'),false)
       AND NOT EXISTS(SELECT 1 FROM work_task WHERE state='running');
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    UPDATE inference_runtime SET uncertain=NOT safe,cycle_token=NULL,
        last_finished=t,last_result=CASE WHEN safe THEN p_result ELSE 'blocked' END
      WHERE singleton;
    RETURN CASE WHEN safe THEN p_result ELSE 'blocked' END;
END;
$finish$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_inference_begin()',
        'penny_inference_finish(uuid,text)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
