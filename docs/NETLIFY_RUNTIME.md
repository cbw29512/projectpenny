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
function configuration remains a prerequisite.
Member auth is operator-issued beta tokens, not a public signup or session
issuer. Cloud admin routes are prohibited. No new expenditure.

## Maker-only administration
Cloud administration runtime removed per the [NucBox-only contract](WEB_ADMIN.md).

## Warm instance configuration safety
Runtime candidates revalidate production context and opt-in on every
request. A warm handler pins a digest of its validated configuration;
changed credentials, roles or origin fail closed rather than silently
using the previous pool or verifier. Restart the process with approved
configuration to rotate credentials. This is not a distributed kill
switch: provider environment updates may require redeployment and
already-running requests are not canceled. Persistent database admission
pause remains independent. No configuration digest or secret is logged.
