# Web administration contract
The same website will host /admin; login must use verified administrator
identity and MFA. No public admin registration. Member or bridge tokens
never grant administrator access. Actual identity provider, verified token
adapter and revocation are required
before any routes are deployed. The current core accepts an injected
trusted verifier, not client-provided role/MFA claims, and defaults closed.
State: independently provisioned cloud admin UUID and enabled flag, scoped
admin DB role, private aggregate mailbox status, audit event on admission
open->closed. No raw conversation, local task/fence, secrets or shell.
GET /api/v1/admin/status: verified admin session, MFA within 15 minutes.
POST /api/v1/admin/pause-admission: MFA within 5 minutes, exact origin,
explicit confirmation string, verified allowlist, mandatory limiter.
Neither API reopens admission or restarts NucBox. A pause closes NEW cloud
questions and claims; already accepted local work can finish. It is NOT
a local emergency stop. SSH retains local recovery, model replacement,
technical maintenance and true service stop. A future separately authorized
outbound admin-command protocol may request bounded local actions.
No web reset, SSH, spending, deployment or identity-change route.
The /admin static preview is public shell only, contains no private data,
does not accept credentials, and offers no working control until wiring.
Provider-specific identity/MFA, scoped connection setup,
privacy controls and deployment approval remain gates. No new spending.

Migration 007 and netlify/admin/limiter.mjs implement dedicated persistent admin attempt limits: 12 status/minute, 360/day; 6 pause/minute, 60/day, globally across approved admins. Fixed rows, independent of public/bridge counters. Denials and malformed responses fail closed. Reapply audited scoped grants after migration. These are provisional application limits; provider-level request abuse and credit exhaustion remain separate launch gates. SSH remains available even if admin budget is exhausted. No runtime wiring or deployment.
