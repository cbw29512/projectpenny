BEGIN;
-- Owner-controlled projection. A dedicated reader receives SELECT on this view
-- only, never base tables. Exclude visitor messages, raw prompts and outcomes.
CREATE OR REPLACE VIEW kiosk_snapshot WITH (security_barrier=true) AS
SELECT jsonb_build_object(
 'sampled_at',floor(extract(epoch FROM clock_timestamp()))::bigint,
 'paused',s.paused,'enabled',i.enabled,'uncertain',i.uncertain,
 'last_started',i.last_started,'last_result',i.last_result,
 'counts',(SELECT coalesce(jsonb_object_agg(state,n),'{}'::jsonb)
           FROM (SELECT state,count(*) AS n FROM work_task
                 WHERE member_id IS NULL GROUP BY state) q),
 'active',(SELECT jsonb_build_object(
     'kind',CASE WHEN w.task_id IS NOT NULL THEN 'workshop'
                 WHEN d.task_id IS NOT NULL THEN 'business draft' ELSE 'internal task' END,
     'title',b.title,'started_at',t.started_at,'lease_until',t.lease_until)
   FROM work_task t LEFT JOIN workshop_task w ON w.task_id=t.id
   LEFT JOIN business_opportunity b ON b.id=w.opportunity_id
   LEFT JOIN business_draft_task d ON d.task_id=t.id
   WHERE t.state='running' AND t.member_id IS NULL),
 'visitor_busy',EXISTS(SELECT 1 FROM work_task WHERE state='running' AND member_id IS NOT NULL),
 'latest_plan',(SELECT jsonb_build_object('outcome',outcome,'recorded_at',recorded_at)
                FROM hourly_plan ORDER BY hour_slot DESC LIMIT 1),
 'latest_measurement',(SELECT jsonb_build_object(
     'title',b.title,'metric',b.metric,'target',b.target,
     'measured_count',e.measured_count,'recorded_at',e.recorded_at)
   FROM business_experiment_event e JOIN business_opportunity b ON b.id=e.opportunity_id
   WHERE e.action='measured' ORDER BY e.sequence DESC LIMIT 1),
 'finance',(SELECT CASE WHEN count(*)=0 THEN NULL ELSE jsonb_build_object(
     'net_receipts',coalesce(sum(amount) FILTER (WHERE kind='commercial_receipt'),0)-coalesce(sum(amount) FILTER (WHERE kind='commercial_refund'),0),
     'expenses',coalesce(sum(amount) FILTER (WHERE kind IN ('operating_expense','founder_paid_expense','payment_fee')),0),
     'recorded_cash',coalesce(sum(amount) FILTER (WHERE kind IN ('commercial_receipt','community_support','founder_funding')),0)-coalesce(sum(amount) FILTER (WHERE kind IN ('commercial_refund','operating_expense','payment_fee')),0),
     'community_support',coalesce(sum(amount) FILTER (WHERE kind='community_support'),0),
     'status','recorded_unreconciled') END
   FROM (SELECT kind,CASE WHEN reversal_of IS NULL THEN cents ELSE -cents END AS amount
         FROM vault_entry WHERE kind NOT IN ('founder_income','founder_expense')) v),
 'recent',(SELECT coalesce(jsonb_agg(to_jsonb(r) ORDER BY r.finished_at DESC,r.task_id),'[]'::jsonb)
   FROM (SELECT t.id AS task_id,o.finished_at,
       CASE WHEN w.task_id IS NOT NULL THEN 'workshop' ELSE 'business draft' END AS kind,
       coalesce(b.title,c.title) AS title,o.status,
       c.hypothesis,c.metric,c.target,a.content AS prototype
     FROM work_task t JOIN task_outcome o ON o.task_id=t.id
     LEFT JOIN business_draft_task d ON d.task_id=t.id
     LEFT JOIN business_draft_candidate c ON c.task_id=d.task_id
     LEFT JOIN workshop_task w ON w.task_id=t.id
     LEFT JOIN business_opportunity b ON b.id=w.opportunity_id
     LEFT JOIN workshop_artifact a ON a.task_id=w.task_id
     WHERE t.member_id IS NULL AND (d.task_id IS NOT NULL OR w.task_id IS NOT NULL)
     ORDER BY o.finished_at DESC,t.id LIMIT 5) r)
) AS snapshot
FROM scheduler_control s CROSS JOIN inference_runtime i
WHERE s.singleton AND i.singleton;
REVOKE ALL ON kiosk_snapshot FROM PUBLIC;
COMMIT;
