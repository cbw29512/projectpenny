# Workshop browser delivery
CI 46073922191 passed prior publisher and runtime changes. Added explicit
visitor refresh reader with same-origin fixed path, no credentials, cache,
redirect or storage, five-second abort, 1024-byte response cap, one-minute
local cooldown and bounded Retry-After. Validated fixed stage vocabulary and
maximum remaining lease; stale/regressive/conflicting data is suppressed.
Local UI redraw only; never automatic requests. Server remains responsible
for rate limits (browser cooldown is not an abuse boundary).
Static page data-live=false, disabled button and connect-src none remain.
Enable only after actual provider limiter, deployment, isolated DB roles,
key setup and end-to-end rehearsal. No live API or database provisioning.
New Netlify project recorded in NETLIFY_PREFLIGHT. CI pending.

## Shared admission budget (mailbox 011)
CI 46077033096 passed browser delivery. Global fixed-size database buckets
admit at most 60 reads/minute and 1800/day; signed writes 2/minute and
1440/day. Provisional launch ceilings, not cost guarantees. Atomic row locks
serialize concurrent attempts; counters resist backward clock movement.
Existing projection reader/writer gain only their respective limiter routine.
Runtime checks separately supplied provider edge limiter before DB budget;
SQL quota covers admitted application operations, not rejected HTTP invocation
or limiter-query cost. A trusted runtime role could call its existing raw
routine directly; this is not a DB-enforced combined read/write cap against
compromised credentials. Actual edge policy, credit/recharge review, runtime
role provisioning and live deployment still pending. No provider changes.
CI pending; parallel SQL and runtime tests added.
