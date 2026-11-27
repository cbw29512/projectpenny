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
