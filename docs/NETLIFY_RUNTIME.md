# Netlify runtime candidate (not deployed)
State: explicit enabled flag (default closed), production deploy context,
canonical HTTPS origin, two separate role names/connection strings and
separate HMAC keys. No use of ambient NETLIFY_DB_URL, role switching, URI
query overrides or database-owner fallback. The candidate composition uses
the existing gateway, limiter and repository with pg-compatible Pool
injection. Each query verifies its actual current and session principal,
no privileged flags, memberships, schema CREATE or schema ownership, on
the same checked-out client before executing the parameterized routine.
TLS verification and bounded connection/query settings; no direct HTTP
calls to local inference. Pool limits per instance are not global caps.
The check is defense in depth, not a full effective privilege audit.
Provider must support distinct scoped login roles; verify in disposable
branch first. Netlify documents pg-compatible drivers and function
Request/Response exports:
https://docs.netlify.com/build/data-and-storage/netlify-database/tooling/
https://docs.netlify.com/build/functions/get-started/
https://docs.netlify.com/build/functions/configuration/
No runtime package installed, functions directory entrypoint, secrets,
actual DB connection or deployment created. Candidate deliberately lives
outside default functions directory. Actual driver pin/lockfile, approved
scoped role provisioning, provider edge/credit gates, real TLS validation,
admin MFA adapter and function configuration remain prerequisites.
Member auth is operator-issued beta tokens, not a public signup or session
issuer. Admin routes remain disabled. No new expenditure.

## Admin composition candidate
Independent production-only PENNY_ADMIN_ENABLED gate and explicit admin
connection with role distinct from member and bridge. Reuses checked-client
principal validation, TLS options, persistent admin limiter and existing
admin routines. Requires an injected trusted provider verifier; missing
verifier fails closed. No actual MFA provider or login implemented. No
function entrypoint, driver installation, provisioning or deployment.
Five synthetic Node tests exercise composition and failure boundaries.
