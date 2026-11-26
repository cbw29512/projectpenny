# Defense in depth: attention budgets and permanent identity
Migration 012 adds indexes for rolling member admission counts. Within the
existing scheduler lock, new accepted member requests are limited to 3/hour
and 10/24h free, 10/hour and 30/24h paid; aggregate community limits are
20/hour and 120/24h. These are provisional beta ceilings, not purchased
entitlements. Business work does not consume community quota. Existing
queue limits, per-member outstanding limits and one active inference remain.
Count accepted rows regardless of outcome; replay returns original receipt
and does not spend quota again. Rejections insert no new task. A failed count
rolls back admission. Use DB clock; no session reset or account rotation can
exceed aggregate acceptance. Preserve quota facts for at least 24h when
adding retention; expiry must not create a reset.

These caps bound accepted local work, not all HTTP attempts or cost: global
exhaustion can deny service to legitimate users. Cloud edge rate limits,
verified account creation, abuse controls, bounded request bytes, read/poll
limits, connection caps, retry-after, automatic backoff, credit monitoring
and adversarial load tests are mandatory before opening public chat.
No claim of DDoS immunity. Never bill or grant extra capacity automatically.

The v0.2 prompt corrects omissions against the already-approved constitution,
not a change of character. Guardian pins version/hash, blocks new admission
on mismatch, and the child verifies the pin before inference. All actors
remain denied runtime identity changes. Certification v2 adds mission focus
to the suite. No prompt hash proves behavioral invariance: read-only signed
release artifacts, least-privilege OS permissions, live certification and
reviewed output before public delivery remain necessary. Runtime memory is
untrusted context. No model-written code or identity updates.
