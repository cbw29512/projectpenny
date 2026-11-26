BEGIN;
-- Rolling admission windows count all accepted member work, including failed
-- and canceled jobs; no reset by reconnecting, completing or deleting a reply.
CREATE INDEX member_admissions_by_owner_time ON work_task(member_id,submitted_at)
WHERE member_id IS NOT NULL;
CREATE INDEX member_admissions_by_time ON work_task(submitted_at)
WHERE member_id IS NOT NULL;
COMMIT;
