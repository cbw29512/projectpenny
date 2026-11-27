BEGIN;
-- Candidate cloud read model: one bounded row, independent of chat admission.
-- No private text, identifiers, or authority to perform local work.
CREATE TABLE activity_observation (
    singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
    enabled boolean NOT NULL DEFAULT false,
    sampled_at bigint NOT NULL DEFAULT 0 CHECK(sampled_at>=0),
    received_at bigint NOT NULL DEFAULT 0 CHECK(received_at>=sampled_at),
    activity text CHECK(activity IN ('idle','working','draining','paused','blocked','off_duty')),
    CHECK((sampled_at=0)=(activity IS NULL))
);
INSERT INTO activity_observation DEFAULT VALUES;

CREATE FUNCTION activity_publish(p_sample bigint,p_activity text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $publish$
DECLARE
    current_row activity_observation%ROWTYPE;
    now_epoch bigint;
BEGIN
    SELECT * INTO current_row FROM activity_observation WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT current_row.enabled THEN RETURN false; END IF;
    now_epoch:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    IF p_sample IS NULL OR p_sample<=0 OR p_sample>now_epoch
       OR p_sample<=now_epoch-15 OR p_activity IS NULL
       OR p_activity NOT IN ('idle','working','draining','paused','blocked','off_duty')
    THEN RETURN false; END IF;
    IF p_sample=current_row.sampled_at THEN
        RETURN p_activity=current_row.activity;
    END IF;
    -- Database time and monotonic sample prevent replay or refresh of stale data.
    -- Distinct writes are spaced to avoid tight retries; never extend a sample TTL.
    IF p_sample<current_row.sampled_at OR now_epoch<current_row.received_at+45
    THEN RETURN false; END IF;
    UPDATE activity_observation SET sampled_at=p_sample,received_at=now_epoch,
        activity=p_activity WHERE singleton;
    RETURN true;
END;
$publish$;

CREATE FUNCTION activity_read()
RETURNS TABLE(sampled_at bigint,activity text)
LANGUAGE sql SECURITY DEFINER AS $read$
    SELECT o.sampled_at,o.activity FROM activity_observation o
    WHERE o.singleton AND o.enabled AND o.sampled_at>0
      AND o.sampled_at<=floor(extract(epoch FROM clock_timestamp()))::bigint
      AND o.sampled_at>floor(extract(epoch FROM clock_timestamp()))::bigint-120;
$read$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
    EXECUTE format('REVOKE ALL ON TABLE %I.activity_observation FROM PUBLIC',ns);
    FOREACH signature IN ARRAY ARRAY['activity_publish(bigint,text)','activity_read()'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
