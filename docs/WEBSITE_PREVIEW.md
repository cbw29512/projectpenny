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
