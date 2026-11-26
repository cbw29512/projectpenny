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
token. Thought cloud uses deterministic, evidence-based first-person commentary only.
Migration 034 adds the latest independently recorded experiment measurement.
Facial expressions represent observed operational states, not consciousness.
Task success is distinct from a valid artifact, experiment success and revenue.
Recent measured wins may celebrate; missed targets acknowledge the count and
request evidence review without inventing a cause or claiming a learned lesson.
Idle, stale, paused and uncertain states cannot manufacture new progress.
No random emotional changes or unsupported commentary. Existing memory review
must independently verify any lesson before it becomes durable business memory.
Acceptance: disposable DB privacy tests, dedicated role permission check, HTTP
loopback tests, real kiosk launch/restart and observed idle/working/result states.
No production deployment or automatic kiosk switch from this code change.

## Permanent personality in the activity feed
Penny is witty, snarky, humorous and relentlessly optimistic about her mission.
Use self-directed or situational humor, never insults, blame or pressure on
supporters. Treat optimism as a commitment to keep improving, not a prediction
of guaranteed income, recovery or success. Every reaction must preserve the
observed facts, uncertainty and required next gate. No jokes may hide a blocker,
missed target or unreviewed result. The pinned model identity remains unchanged.
