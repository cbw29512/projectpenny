BEGIN;
-- Narrow activity-only routines. No runtime grants are installed here.
-- Owner must be the dedicated trusted schema owner in production.
CREATE FUNCTION penny_activity_reserve(p_binding text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER AS $reserve$
DECLARE
    c scheduler_control%ROWTYPE;
    r activity_delivery_control%ROWTYPE;
    t bigint;
    bucket bigint;
    used integer;
BEGIN
    SELECT * INTO c FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR c.paused THEN RETURN 'paused'; END IF;
    SELECT * INTO r FROM activity_delivery_control WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT r.enabled OR p_binding IS NULL OR
       r.config_sha256 IS DISTINCT FROM p_binding THEN RETURN 'paused'; END IF;
    IF r.last_result='interrupted' THEN RETURN 'review_required'; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    IF t<r.not_before THEN RETURN 'cooldown'; END IF;
    bucket:=greatest(t/86400,r.day_bucket);
    used:=CASE WHEN bucket=r.day_bucket THEN r.attempts ELSE 0 END;
    IF used>=r.daily_limit THEN RETURN 'budget_exhausted'; END IF;
    UPDATE activity_delivery_control SET day_bucket=bucket,attempts=used+1,
        not_before=t+60,last_result='interrupted' WHERE singleton;
    RETURN 'reserved';
END;
$reserve$;

CREATE FUNCTION penny_activity_finish(p_result text) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER AS $finish$
DECLARE t bigint;
BEGIN
    PERFORM 1 FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN false; END IF;
    IF p_result IS NULL OR p_result NOT IN
      ('published','refused','unavailable','backoff','unauthorized','uncertain')
    THEN p_result:='uncertain'; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    UPDATE activity_delivery_control SET last_result=p_result,
        enabled=enabled AND p_result='published',
        not_before=greatest(not_before,t+CASE WHEN p_result='backoff' THEN 86400 ELSE 60 END)
    WHERE singleton AND last_result='interrupted';
    RETURN FOUND;
END;
$finish$;

CREATE FUNCTION penny_activity_inputs()
RETURNS TABLE(paused boolean,rest_enabled boolean,inference_enabled boolean,
              uncertain boolean,active_lease bigint,sampled_at bigint)
LANGUAGE plpgsql SECURITY DEFINER AS $inputs$
BEGIN
    PERFORM 1 FROM scheduler_control c WHERE c.singleton FOR UPDATE;
    IF NOT FOUND THEN RETURN; END IF;
    -- No member IDs, payloads, results, financial values or raw table grants.
    RETURN QUERY SELECT c.paused,c.rest_enabled,i.enabled,i.uncertain,
        (SELECT w.lease_until FROM work_task w WHERE w.state='running'),
        floor(extract(epoch FROM clock_timestamp()))::bigint
      FROM scheduler_control c CROSS JOIN inference_runtime i
      WHERE c.singleton AND i.singleton;
END;
$inputs$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_activity_reserve(text)',
        'penny_activity_finish(text)','penny_activity_inputs()'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
