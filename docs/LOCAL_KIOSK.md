# Private NucBox kiosk
Objective: physical screen shows real runtime state and committed business drafts,
without altering inference or exposing visitor messages. Use existing Cage/browser
after verifying the actual launcher; no assumption about its service identity.
Schema: migration 033 creates one read-only snapshot view with status, internal
task counts, safe active-task metadata, latest hourly decision and up to five
structured business candidates or inert workshop prototypes. No raw prompts,
visitor text, fences, credentials, financial data or private reasoning.
A dedicated NOINHERIT login receives CONNECT, schema USAGE and SELECT on
kiosk_snapshot only. The owner-created security-barrier view supplies projection.
Run server as a separate unprivileged OS identity, root-owned code and private
config. Bind only 127.0.0.1:18787; do not forward the port or publish to Netlify.
Local users can read the display, so this is a private-room screen, not an
authenticated admin console. Model-generated fields remain untrusted private
drafts. Use textContent, no HTML injection, no remote assets, no mutating routes.
Poll every two seconds after each completed fetch; mark offline/stale on failure.
No new inference, no changes to Guardian or worker; existing non-streaming model
transport is preserved. Output becomes visible after fenced commit, not token by
token. Thought cloud uses explicitly labeled scripted character asides.
Acceptance: disposable DB privacy tests, dedicated role permission check, HTTP
loopback tests, real kiosk launch/restart and observed idle/working/result states.
No production deployment or automatic kiosk switch from this code change.
