BEGIN;
-- Private helpers: validate raw JSON without losing duplicate keys.
-- All authority comes from the stored task and its admission record.
CREATE FUNCTION penny_private_product_text(p_value text,p_limit integer)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $text$
    SELECT coalesce(length(p_value) BETWEEN 1 AND p_limit
        AND btrim(p_value,U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000')<>''
        AND p_value !~ U&'[\0001-\001F]',false)
$text$;

CREATE FUNCTION penny_private_parse_business(p_raw text)
RETURNS TABLE(category text,title text,hypothesis text,metric text,
              target integer,duration_seconds integer,additional_cash_cents bigint)
LANGUAGE plpgsql AS $proposal$
DECLARE j json;
BEGIN
    IF p_raw IS NULL OR length(p_raw) NOT BETWEEN 1 AND 8000 THEN RETURN; END IF;
    j:=p_raw::json;
    IF json_typeof(j) IS DISTINCT FROM 'object' THEN RETURN; END IF;
    IF (SELECT count(*) FROM json_each(j))<>7 OR
       (SELECT count(DISTINCT e.key) FROM json_each(j) e)<>7 OR
       EXISTS(SELECT 1 FROM unnest(ARRAY['category','title','hypothesis','metric']) k(name)
              WHERE json_typeof(j->k.name) IS DISTINCT FROM 'string') OR
       EXISTS(SELECT 1 FROM unnest(ARRAY['target','duration_seconds','additional_cash_cents']) k(name)
              WHERE json_typeof(j->k.name) IS DISTINCT FROM 'number')
    THEN RETURN; END IF;
    category:=j->>'category'; title:=j->>'title';
    hypothesis:=j->>'hypothesis'; metric:=j->>'metric';
    IF category NOT IN ('digital_product','content','software_utility','service_research')
       OR metric NOT IN ('qualified_interest','prototype_checks_passed','validated_requirements')
       OR NOT penny_private_product_text(title,120)
       OR NOT penny_private_product_text(hypothesis,1000)
       OR (j->>'target') !~ '^[0-9]{1,5}$'
       OR (j->>'duration_seconds') !~ '^[0-9]{1,6}$'
       OR (j->>'additional_cash_cents') NOT IN ('0','-0')
    THEN RETURN; END IF;
    target:=(j->>'target')::integer;
    duration_seconds:=(j->>'duration_seconds')::integer;
    additional_cash_cents:=0;
    IF target NOT BETWEEN 1 AND 10000 OR duration_seconds NOT BETWEEN 60 AND 604800
    THEN RETURN; END IF;
    RETURN NEXT;
EXCEPTION WHEN data_exception THEN RETURN;
END;
$proposal$;

CREATE FUNCTION penny_private_render_checklist(p_raw text)
RETURNS text LANGUAGE plpgsql AS $checklist$
DECLARE
    j json;
    item json;
    value text;
    rendered text;
    normalized text;
    seen text[]:=ARRAY[]::text[];
    whitespace constant text:=U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000';
BEGIN
    IF p_raw IS NULL OR length(p_raw) NOT BETWEEN 1 AND 8000 THEN RETURN NULL; END IF;
    j:=p_raw::json;
    IF json_typeof(j) IS DISTINCT FROM 'object' THEN RETURN NULL; END IF;
    IF (SELECT count(*) FROM json_each(j))<>3 OR
       (SELECT count(DISTINCT e.key) FROM json_each(j) e)<>3 OR
       json_typeof(j->'title') IS DISTINCT FROM 'string' OR
       json_typeof(j->'instructions') IS DISTINCT FROM 'string' OR
       json_typeof(j->'items') IS DISTINCT FROM 'array'
    THEN RETURN NULL; END IF;
    IF NOT penny_private_product_text(j->>'title',120)
       OR NOT penny_private_product_text(j->>'instructions',400)
       OR json_array_length(j->'items') NOT BETWEEN 3 AND 12
    THEN RETURN NULL; END IF;
    rendered:=btrim(j->>'title',whitespace)||E'\n\n'||
              btrim(j->>'instructions',whitespace)||E'\n\n';
    FOR item IN SELECT a.value FROM json_array_elements(j->'items') a LOOP
        IF json_typeof(item) IS DISTINCT FROM 'string' THEN RETURN NULL; END IF;
        value:=item#>>'{}';
        IF NOT penny_private_product_text(value,300) THEN RETURN NULL; END IF;
        value:=btrim(value,whitespace);
        -- PostgreSQL 16 lower() is not Python Unicode casefold(). For an
        -- independently enforced SQL boundary, fail closed on non-ASCII
        -- item text until exact folding parity is available. Titles and
        -- instructions retain their existing Unicode support.
        IF octet_length(convert_to(value,'UTF8'))<>length(value) THEN RETURN NULL; END IF;
        normalized:=lower(value COLLATE "C");
        IF normalized=ANY(seen) THEN RETURN NULL; END IF;
        seen:=array_append(seen,normalized);
        rendered:=rendered||'[ ] '||value||E'\n';
    END LOOP;
    IF length(rendered)>6000 THEN RETURN NULL; END IF;
    RETURN rendered;
EXCEPTION WHEN data_exception THEN RETURN NULL;
END;
$checklist$;

DO $secure$
DECLARE ns name:=current_schema(); signature text;
BEGIN
    IF ns IS NULL OR ns IN ('pg_catalog','information_schema') OR ns LIKE 'pg_temp_%'
    THEN RAISE EXCEPTION 'trusted Penny schema required'; END IF;
    FOREACH signature IN ARRAY ARRAY['penny_private_product_text(text,integer)',
        'penny_private_parse_business(text)','penny_private_render_checklist(text)'] LOOP
        EXECUTE format('ALTER FUNCTION %I.%s SET search_path TO pg_catalog, %I, pg_temp',ns,signature,ns);
        EXECUTE format('REVOKE ALL ON FUNCTION %I.%s FROM PUBLIC',ns,signature);
    END LOOP;
END;
$secure$;
COMMIT;
