BEGIN;
-- Private parser and intake. No approval, revocation or arbitrary memory read.
CREATE FUNCTION penny_private_parse_maintenance(p_raw text)
RETURNS TABLE(action text,sources uuid[],rationale text,replacement text)
LANGUAGE plpgsql AS $parse$
DECLARE
    j json;
    item json;
    value text;
    source uuid;
    whitespace constant text:=U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000';
BEGIN
    IF p_raw IS NULL OR length(p_raw) NOT BETWEEN 1 AND 8000 THEN RETURN; END IF;
    j:=p_raw::json;
    IF json_typeof(j) IS DISTINCT FROM 'object' THEN RETURN; END IF;
    IF (SELECT count(*) FROM json_each(j))<>4 OR
       (SELECT count(DISTINCT e.key) FROM json_each(j) e)<>4 OR
       json_typeof(j->'action') IS DISTINCT FROM 'string' OR
       json_typeof(j->'sources') IS DISTINCT FROM 'array' OR
       json_typeof(j->'rationale') IS DISTINCT FROM 'string'
    THEN RETURN; END IF;
    action:=j->>'action';
    IF action NOT IN ('correct','consolidate','outdated','contradiction') OR
       json_array_length(j->'sources') NOT BETWEEN 1 AND 3 THEN RETURN; END IF;
    sources:=ARRAY[]::uuid[];
    FOR item IN SELECT a.value FROM json_array_elements(j->'sources') a LOOP
        IF json_typeof(item) IS DISTINCT FROM 'string' THEN RETURN; END IF;
        value:=item#>>'{}';
        IF value !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        THEN RETURN; END IF;
        source:=value::uuid;
        IF source='00000000-0000-0000-0000-000000000000'::uuid OR source=ANY(sources)
        THEN RETURN; END IF;
        sources:=array_append(sources,source);
    END LOOP;
    IF (action IN ('correct','outdated') AND cardinality(sources)<>1)
       OR (action IN ('consolidate','contradiction') AND cardinality(sources)<2)
    THEN RETURN; END IF;
    value:=j->>'rationale';
    IF length(value) NOT BETWEEN 1 AND 500 THEN RETURN; END IF;
    rationale:=btrim(value,whitespace);
    IF rationale='' THEN RETURN; END IF;
    IF action IN ('correct','consolidate') THEN
        IF json_typeof(j->'replacement') IS DISTINCT FROM 'string' THEN RETURN; END IF;
        value:=j->>'replacement';
        IF length(value) NOT BETWEEN 1 AND 1000 THEN RETURN; END IF;
        replacement:=btrim(value,whitespace);
        IF replacement='' THEN RETURN; END IF;
    ELSE
        IF json_typeof(j->'replacement') IS DISTINCT FROM 'null' THEN RETURN; END IF;
        replacement:=NULL;
    END IF;
    RETURN NEXT;
EXCEPTION WHEN data_exception THEN RETURN;
END;
$parse$;

CREATE FUNCTION penny_private_stage_maintenance(p_task uuid,p_fence uuid,p_raw text,p_now bigint)
RETURNS void LANGUAGE plpgsql AS $stage$
DECLARE p record;
BEGIN
    SELECT * INTO p FROM penny_private_parse_maintenance(p_raw);
    IF NOT FOUND THEN RETURN; END IF;
    -- Every source must belong to one recall event for this task/fence
    -- and remain active under the caller's scheduler transaction lock.
    IF NOT EXISTS(
        SELECT 1 FROM memory_recall_event e
        JOIN memory_recall_source s ON s.event_id=e.id
        JOIN business_memory m ON m.source_task_id=s.source_task_id
        WHERE e.task_id=p_task AND e.fence=p_fence
          AND m.revoked_at IS NULL AND m.expires_at>p_now
          AND s.source_task_id=ANY(p.sources)
        GROUP BY e.id HAVING count(DISTINCT s.source_task_id)=cardinality(p.sources)
    ) THEN RETURN; END IF;
    INSERT INTO memory_maintenance_proposal(task_id,action,rationale,replacement,created_at,policy_version)
      VALUES(p_task,p.action,p.rationale,p.replacement,p_now,'guardian-v0.22');
    INSERT INTO memory_maintenance_source(task_id,source_task_id)
      SELECT p_task,s.id FROM unnest(p.sources) AS s(id);
END;
$stage$;
DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_private_parse_maintenance(text)',
        'penny_private_stage_maintenance(uuid,uuid,text,bigint)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature,ns);
    END LOOP;
END;
$secure$;
COMMIT;
