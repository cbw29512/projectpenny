# Static game homepage — first implementation
Objective: show Penny's scene, dialogue, local question preview, mission,
Achievement Center, greatest contributors and diary in an accessible,
responsive single page before any public request endpoint exists.

State: unavailable/live-not-connected, draft text (browser memory only),
length, preview eligibility, local notice. No synthetic financial progress,
verified achievements, contributors or actual generated answers.
Controls start disabled and initialize only after JavaScript loads.
Preview button never submits or clears draft. Render status via textContent.

Run from repo root: python -m http.server 8000 --bind 127.0.0.1 --directory website
Open http://127.0.0.1:8000/ locally. Tests: node --test tests/web/*.test.mjs.
The root netlify.toml publishes only website/. Static _headers block
connections/forms and framing. A plain local HTTP server does not apply these
headers; check them on an authorized Netlify preview. Do not merge into
the production deploy branch until explicitly approved. Preview is public-safe
synthetic content, noindex is not access control. No DB, keys, API, paid
services or external assets. Final character art still requires approval.
Next: authenticated mailbox migrations and transactional claim/answer flow;
enable live submit and network CSP only after security acceptance.

## Private beta browser protocol candidate
The separate beta-mailbox modules implement explicitly enabled, in-memory
operator-issued member credentials, one outstanding draft and exact key/text
replay after ambiguous submit, owner-bound reply validation, bounded response
stream, request timeout, manual read and 15-second minimum request spacing.
No browser storage, automatic polling, third-party endpoint or redirect.
Sign-out clears local state; there is no durable recovery after reload yet.
The public preview does not import this candidate and CSP remains closed.
The synthetic browser-to-real-gateway handler test exercises response loss,
replay and owner-validated reply, not a deployed database/bridge round trip.
Next: approved private beta UI and identity/session integration; no live
credentials, CSP relaxation, deployment or new spend in this change.

## Private conversation interface candidate
The separate private-beta/ directory contains a responsive credential and
conversation interface, deliberately excluded from the website/ publish root.
It starts disabled, requires a secure HTTPS context and uses only the
same-origin mailbox protocol. A credential loaded locally is not called
verified until a server response. The original draft stays locked on an
ambiguous receipt; explicit retry reuses the client key and text. Replies
use textContent only. Clear session/pagehide removes credentials, draft
and reply; no storage or automatic polling. An expired credential with an
outstanding question requires operator assistance; durable reload/recovery
and safe credential renewal are not implemented. This page does not create
access control: an approved isolated HTTPS host, response security headers,
scoped gateway and issued credentials are prerequisites. Do not publish
this directory by changing the public deploy root. Tests exercise the UI
binding with synthetic responses, including late response after sign-out;
no actual hosted browser or NucBox has been certified. No live deployment.

## Private beta activity reader
The isolated HTTPS beta includes a manual same-origin GET /api/v1/activity
reader. It uses a 512-byte response bound, five-second fetch abort, minimum
60-second page-local interval, provider Retry-After and monotonic observation
validation. Stale, conflicting, malformed or unavailable samples clear the
view. Display uses fixed Last observed labels and original UTC timestamps;
local rendering expires them after 120 seconds without network polling.
Pagehide closes the reader. No session credentials, browser storage, redirects,
chat or sleep-state changes. Public homepage and network CSP are unchanged.
Page-local limits are not abuse protection: provider edge/admission gate,
approved host, real browser rehearsal and CI remain mandatory.
