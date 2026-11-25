# Private learning intake — first slice

## Definition of done
A trusted internal caller can queue a bounded learning review using the existing
exclusive scheduler. Penny proposes at most one typed candidate. Only a successful
fenced internal review can store a candidate, atomically with its private outcome.
Member tasks, malformed proposals, stale fences and denied Guardian checks cannot
create candidates. No candidate is automatically trusted, recalled, or published.

## State/schema
Memory candidate: source_task_id (primary key, foreign key to task_outcome),
kind (lesson, failure, idea, skill, milestone), content (1–1000 characters),
scope (private_business), validation_state (quarantined), created_at (UTC instant).
The database supplies scope/state and time. The model only supplies kind/content.
Source task identity records provenance, not evidence of factual accuracy.
This is a staging table, not the final memory_record schema.

## Logic
Trusted caller -> submit_review -> existing bounded queue -> local model draft ->
Guardian draft check -> fenced completion -> Guardian candidate check ->
strict candidate parse -> quarantine insert in same transaction as task outcome.
Invalid or denied proposals remain private drafts; a storage exception rolls back
the outcome and candidate. Retry/recovery follows existing conservative lease rules.

Apply migrations 001 then 002 before submitting review jobs. No new dependency
or inference endpoint. Existing normal draft behavior remains unchanged.
No new public route, recall, user memory, external actions, or trusted writes.

## Still required
Independent evidence linking/validation and approval, consent and deletion/retention,
owner-scoped member records, bounded recall with explicit untrusted-data framing,
deduplication across reviews, quota/retention limits, durable policy audit and
correction/revocation. Candidate text may contain false claims, personal data or
prompt injection; do not feed it into active context. Deployment must restrict
database and process privileges; this module is not OS isolation. Do not run
unattended review admission before quotas and retention are in place.
