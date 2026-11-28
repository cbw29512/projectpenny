BEGIN;
-- Sanitized single-product observation, disabled until owner provisioning.
CREATE TABLE workshop_observation (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 enabled boolean NOT NULL DEFAULT false,
 sampled_at bigint NOT NULL DEFAULT 0,
 received_at bigint NOT NULL DEFAULT 0,
 stage text NOT NULL DEFAULT 'unavailable' CHECK(stage IN
 ('unavailable','prototype_reviewed','preview_reviewed','revision_reviewed','review_withdrawn')),
 generated_at bigint NOT NULL DEFAULT 0,
 expires_at bigint NOT NULL DEFAULT 0,
 CHECK(sampled_at>=0 AND received_at>=sampled_at),
 CHECK((stage='unavailable' AND generated_at=0 AND expires_at=0) OR
 (stage<>'unavailable' AND generated_at>0 AND generated_at<=sampled_at
 AND expires_at>sampled_at AND expires_at<=sampled_at+120 AND expires_at<=generated_at+3600))
);
INSERT INTO workshop_observation DEFAULT VALUES;

CREATE FUNCTION workshop_publish(p_sample bigint,p_stage text,p_generated bigint,p_expiry bigint)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $publish$
DECLARE current_row workshop_observation%ROWTYPE; n bigint;
BEGIN
 SELECT * INTO current_row FROM workshop_observation WHERE singleton FOR UPDATE;
 IF NOT FOUND OR NOT current_row.enabled THEN RETURN false; END IF;
 n:=floor(extract(epoch FROM clock_timestamp()))::bigint;
 IF p_sample IS NULL OR p_sample<=0 OR p_sample>n OR p_sample<=n-15
 OR p_stage IS NULL OR p_generated IS NULL OR p_expiry IS NULL
 OR NOT ((p_stage='unavailable' AND p_generated=0 AND p_expiry=0) OR
 (p_stage IN ('prototype_reviewed','preview_reviewed','revision_reviewed','review_withdrawn')
 AND p_generated>0 AND p_generated<=p_sample AND p_expiry>n
 AND p_expiry<=p_sample+120 AND p_expiry<=p_generated+3600))
 THEN RETURN false; END IF;
 IF p_sample=current_row.sampled_at THEN
  RETURN (p_stage,p_generated,p_expiry)=(current_row.stage,current_row.generated_at,current_row.expires_at);
 END IF;
 IF p_sample<current_row.sampled_at OR n<current_row.received_at+45 THEN RETURN false; END IF;
 UPDATE workshop_observation SET sampled_at=p_sample,received_at=n,stage=p_stage,
 generated_at=p_generated,expires_at=p_expiry WHERE singleton;
 RETURN true;
END;
$publish$;

CREATE FUNCTION workshop_read()
RETURNS TABLE(sampled_at bigint,stage text,generated_at bigint,expires_at bigint)
LANGUAGE sql SECURITY DEFINER AS $read$
 SELECT o.sampled_at,o.stage,o.generated_at,o.expires_at FROM workshop_observation o
 WHERE o.singleton AND o.enabled AND o.stage<>'unavailable'
 AND o.sampled_at<=floor(extract(epoch FROM clock_timestamp()))::bigint
 AND o.expires_at>floor(extract(epoch FROM clock_timestamp()))::bigint;
$read$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
 IF ns IS NULL OR ns IN ('public','pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
 THEN RAISE EXCEPTION 'dedicated mailbox schema required'; END IF;
 EXECUTE format('REVOKE ALL ON TABLE %I.workshop_observation FROM PUBLIC',ns);
 FOREACH signature IN ARRAY ARRAY['workshop_publish(bigint,text,bigint,bigint)','workshop_read()'] LOOP
  EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
  EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
 END LOOP;
END;
$secure$;
COMMIT;
