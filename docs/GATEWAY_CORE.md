# Authenticated gateway core — private beta, not deployed
Objective: strict typed HTTP boundary between browser, cloud mailbox and
outbound NucBox worker. No generic SQL or remote tool routes.
State: member/bridge scope, verified subject, short-lived signed bearer
credential (15 min maximum), request operation, bounded JSON and receipt.
Separate HMAC keys, minimum 32 bytes each, owner derived only from verified
token. No session cookie, URL token, client role, claimed member tier or owner
field. Token issuance and rotation remain operator-only future work; do not
give anyone the signing keys. No real credentials in Git.
Logic: closed unless explicitly enabled -> exact origin/path/method ->
scope verification -> mandatory injected rate limiter -> bounded streaming
JSON -> strict schema -> scoped parameterized query -> allowlisted response.
All responses private/no-store; no cross-origin allowance. No body/secret logs.
Code uses Node 22 built-ins and standard Request/Response. Repository requires
separate query adapters using fixed penny_mailbox schema. No external package.
Tests: node --test tests/web/*.test.mjs.
This core is not in a Netlify functions directory and no endpoint is live.
Netlify runtime adapter, actual separate DB credentials, token provisioning,
distributed attempt/read limiter and provider-level edge controls remain
required. In-memory rate limiting would not protect serverless instances.
HMAC bearer theft permits replay until expiry; per-member disable at DB,
key rotation, local bridge replay mapping and proper identity provider needed
before public use. Need bounded connection/statement/body read timeouts at
runtime and verified zero-cost credits. Gateway does not certify model output.
No direct NucBox listener, deployment or new expenditure.
