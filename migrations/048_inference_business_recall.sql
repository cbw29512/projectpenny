BEGIN;
-- No caller-selected search query, member, source ID or trust level.
CREATE FUNCTION penny_inference_business_recall(p_cycle uuid,p_task uuid,p_fence uuid)
RETURNS TABLE(source_task_id uuid,kind text,content text)
LANGUAGE plpgsql SECURITY DEFINER AS $recall$
DECLARE
    ctl scheduler_control%ROWTYPE;
    gate inference_runtime%ROWTYPE;
    task work_task%ROWTYPE;
    t bigint;
    topic text;
    expression text;
    prefix constant text:=$prompt$Review supplied historical memories for the topic below. Return one JSON object with action (correct, consolidate, outdated, contradiction), sources (list of recalled source UUIDs), rationale (max 500 chars), replacement (max 1000 chars for correct/consolidate, null otherwise). Correct/outdated use one source; consolidate/contradiction use two or three distinct sources. Return {} if insufficient evidence. Do not claim verification. Topic: $prompt$;
    event_id uuid;
    record_row record;
    normalized text;
    seen text[]:=ARRAY[]::text[];
    selected uuid[]:=ARRAY[]::uuid[];
    remaining integer:=1500;
BEGIN
    SELECT * INTO ctl FROM scheduler_control WHERE singleton FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'scheduler unavailable'; END IF;
    SELECT * INTO gate FROM inference_runtime WHERE singleton FOR UPDATE;
    IF NOT FOUND OR NOT gate.uncertain OR p_cycle IS NULL OR
       gate.cycle_token IS DISTINCT FROM p_cycle OR
       gate.claim_cycle_token IS DISTINCT FROM p_cycle
    THEN RAISE EXCEPTION 'invalid inference cycle'; END IF;
    IF ctl.paused OR NOT gate.enabled THEN RETURN; END IF;
    t:=floor(extract(epoch FROM clock_timestamp()))::bigint;
    SELECT w.* INTO task FROM work_task w
      WHERE w.id=p_task AND w.fence=p_fence AND w.state='running'
        AND w.lease_until>t AND w.member_id IS NULL
        AND starts_with(w.idempotency_key,'memory-informed:');
    IF NOT FOUND THEN RETURN; END IF;
    IF EXISTS(SELECT 1 FROM memory_recall_event e WHERE e.task_id=p_task AND e.fence=p_fence)
    THEN RAISE EXCEPTION 'business recall already performed'; END IF;
    topic:=task.payload;
    IF starts_with(task.idempotency_key,'memory-informed:maintenance-') THEN
        IF starts_with(topic,prefix) THEN
            topic:=substring(topic FROM length(prefix)+1);
            IF length(topic)>1000 OR topic !~ '[^[:space:]]' THEN topic:=''; END IF;
        ELSE topic:=''; END IF;
    END IF;
    -- ASCII lexical terms only, stable first occurrence and bounded length.
    -- PostgreSQL lower/whitespace semantics require Unicode parity review.
    SELECT string_agg(s.word,' OR ' ORDER BY s.first_position) INTO expression
      FROM (SELECT m.parts[1] AS word,min(m.position) AS first_position
            FROM regexp_matches(lower(topic) COLLATE "C",'[a-z0-9]{2,32}','g')
              WITH ORDINALITY AS m(parts,position)
            WHERE m.parts[1]<>'or'
            GROUP BY m.parts[1] ORDER BY min(m.position) LIMIT 32) s;
    IF expression IS NOT NULL THEN
        FOR record_row IN
            WITH q AS (SELECT websearch_to_tsquery('pg_catalog.english'::regconfig,expression) AS terms)
            SELECT b.source_task_id,b.kind,b.content
            FROM business_memory b CROSS JOIN q
            WHERE b.revoked_at IS NULL AND b.expires_at>t
              AND to_tsvector('pg_catalog.english'::regconfig,b.content) @@ q.terms
            ORDER BY ts_rank(to_tsvector('pg_catalog.english'::regconfig,b.content),q.terms) DESC,
                     b.approved_at DESC,b.source_task_id LIMIT 24
        LOOP
            normalized:=btrim(regexp_replace(lower(record_row.content),'[[:space:]]+',' ','g'));
            IF normalized=ANY(seen) OR length(record_row.content)>remaining THEN CONTINUE; END IF;
            seen:=array_append(seen,normalized);
            selected:=array_append(selected,record_row.source_task_id);
            remaining:=remaining-length(record_row.content);
            EXIT WHEN cardinality(selected)=3;
        END LOOP;
    END IF;
    event_id:=gen_random_uuid();
    INSERT INTO memory_recall_event(id,task_id,fence,recorded_at,policy_version,rank_version,selected_count)
      VALUES(event_id,p_task,p_fence,t,'guardian-v0.22','english-lexical-v2-sql',cardinality(selected));
    INSERT INTO memory_recall_source(event_id,source_task_id,position)
      SELECT event_id,s.id,s.position::integer FROM unnest(selected) WITH ORDINALITY AS s(id,position);
    -- The source audit and response are transactional; rollback on any error.
    RETURN QUERY SELECT b.source_task_id,b.kind,b.content FROM unnest(selected)
        WITH ORDINALITY AS s(id,position)
      JOIN business_memory b ON b.source_task_id=s.id ORDER BY s.position;
END;
$recall$;

DO $secure$
DECLARE ns name:=current_schema();
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    EXECUTE format('ALTER FUNCTION %I.penny_inference_business_recall(uuid,uuid,uuid) SET search_path TO pg_catalog, %I, pg_temp',ns,ns);
    EXECUTE format('REVOKE ALL ON FUNCTION %I.penny_inference_business_recall(uuid,uuid,uuid) FROM PUBLIC',ns);
END;
$secure$;
COMMIT;
