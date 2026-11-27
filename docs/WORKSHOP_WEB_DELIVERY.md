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

## Staged provider edge rules
CI 46077964034 passed shared database budgets. Netlify's current Pro plan
supports five code-based rules and per-IP/domain aggregation (not a shared
domain-only cap). Two staged smoke functions export literal path/method
and rateLimit config: GET /api/v1/workshop 6 per IP/minute and POST
/api/v1/bridge/workshop 3 per IP/minute. Both always return unavailable,
with no database or secret dependency; default netlify.toml is unchanged.
The remaining three rule slots are reserved for future community APIs.
Netlify can allow bursts for up to ten seconds; invalid rate-limit rules do
not necessarily fail a deploy. Verify both rules in post-processing logs
and controlled 429 behavior before enabling the data path. Entry guard
binds exact origin/site ID and trusted published production deploy context
plus explicit reviewed deploy ID. It is an attestation, not proof of edge
behavior; the final activation mechanism must accommodate Netlify's
redeploy-on-env-change semantics without assuming env changes take effect
on an existing deploy. No actual deployment, DB driver, live edge proof,
credentials, or new charges. CI pending.
References:
https://docs.netlify.com/manage/security/secure-access-to-sites/rate-limiting/
https://docs.netlify.com/build/functions/configuration/
https://docs.netlify.com/build/functions/api/
https://docs.netlify.com/build/functions/environment-variables/

## Draft smoke rehearsal
CI 46083596964 passed edge staging. Dedicated smoke routes now support the
exact provider draft hostname and return a fixed marker. The production
entry remains separate and disconnected. See NETLIFY_SMOKE.md for bounded
13-request probe and manual draft procedure. No deployment or requests run.
