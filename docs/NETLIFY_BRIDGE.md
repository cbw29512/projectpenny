# Deployment decision: Netlify public gateway / NucBox private brain
Status: approved direction, implementation pending. Zero additional spending.
No Supabase dependency. Use native Netlify Database (managed PostgreSQL)
subject to the actual account plan, measured credits and launch approval.
GitHub publishes the website from an approved branch; private releases on
NucBox require separate operator approval. No auto-updates from public deploys.

## Data ownership / state first
Public database is a limited temporary mailbox, not Penny's permanent memory:
- authenticated member: opaque subject, status, approved display alias;
  identity provider and session verification still to implement.
- question: UUID, authenticated subject, idempotency key, text (max 2000
  characters), submitted/expires timestamps, status, lease epoch, lease expiry.
  Unique owner + idempotency key; conflicting payload denied.
- reply: unique question ID, owner-bound, bounded plain text, status,
  created/expires timestamps, delivery sequence. Never public or CDN cached.
- bridge receipt: request UUID, fence, local task ID; durable idempotency
  mapping on NucBox, not publicly readable.
- public snapshot: monotonic sequence, generated_at, expires_at, schema
  version, allowlisted metrics, chapter, verified achievements, opted-in
  contributor recognition, status, sanitized timeline. No raw records.
Local PostgreSQL retains canonical scheduler, memory, private ledger, evidence,
business state and outbox. Public database never holds local credentials,
raw logs, network addresses, memory corpus, or administrative control state.

## Proposed HTTPS API (version 1; not implemented)
Browser:
- POST /api/v1/questions: authenticated, strict bounded JSON, owner from
  verified session, idempotency key, rate limits, capacity and freshness check.
- GET /api/v1/questions/:id: authenticated owner-only state and reply;
  private/no-store; no data leakage on foreign identifiers.
- GET /api/v1/world: cacheable sanitized public projection and freshness.
- GET /api/v1/progress: bounded cached timeline.
Bridge (dedicated scoped credentials distinct from member/administrator):
- POST /api/v1/bridge/claim: claim bounded eligible work with lease/fence.
- POST /api/v1/bridge/ack: acknowledge durable local admission, or reject
  with allowlisted status; never trust cloud-supplied membership tier.
- POST /api/v1/bridge/answer: submit approved reply by request ID/fence;
  idempotent and owner resolved from stored request, not model text.
- POST /api/v1/bridge/snapshot: publish validated monotonic snapshot.
- POST /api/v1/bridge/heartbeat: bounded availability/health only, preferably
  batched into claim/snapshot operations to reduce database wakeups.
No arbitrary SQL, generic remote commands, remote URLs, admin endpoints,
direct model calls or local service exposure via the gateway.

## Flow / failure semantics
Browser -> Netlify function authenticates and validates -> database queues
question -> NucBox outbound HTTPS claims -> independently checks envelope,
expiry, local entitlement and capacity -> durable local admission -> Penny
generates draft -> local output and publication review -> outbox -> bridge
uploads result -> owner polls status -> dialogue bubble displays reply.
Lease expiry, retries and network loss must not duplicate local execution:
transactional claiming, durable local request mapping, stale fence rejection,
idempotent upload and explicit reconciliation. Failed admission is reported
honestly, not silently lost or charged. Initial beta only; no live billing.
State: submitted -> claimed -> locally_accepted -> answered; or terminal
rejected/expired/failed/canceled. Busy and offline are availability states,
not fabricated replies. Expiry and retention policy TBD before launch;
delete acknowledged temporary mailbox content per approved policy.

## Security / spending
NucBox initiates HTTPS only. No inbound port forwarding or tunnel; egress
allowlist and separate network/container boundaries. No local DB or Ollama
access from public infrastructure. Model proposes typed tool intents;
trusted bridge performs authenticated narrow API calls after policy checks.
Treat compromised gateway as hostile; external requests cannot change
identity, assign entitlements, spend, access secrets, or invoke arbitrary tools.
Browser never receives DB credentials. Server functions enforce ownership,
parameterized queries, request caps, CSRF/origin controls as appropriate,
secure session handling, output escaping, privacy and log minimization.
Separate worker scopes and public projection from private replies.
No paid hosting, paid API, automatic recharge or new spend. Netlify Database
uses credits for active compute and bandwidth. Account entitlement, quotas,
sleep behavior and remaining shared-team credits must be checked. Poll
adaptively, batch operations, stop idle browser polling, use jitter/backoff
and cached snapshots; benchmark actual database wake costs before selecting
poll interval. If budget exhausted, halt admission and display stale/offline
where hosting remains available. Free service may pause entirely; no SLA.
Use synthetic data in deploy previews and no production secrets.
Sources: https://docs.netlify.com/build/data-and-storage/netlify-database/
https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/

## Acceptance
Authenticated owner-only reads; forged credentials rejected; stale leases and
duplicate uploads rejected; local queue caps and policy override cloud data;
malicious payloads cannot gain tool access; outage/restart recovery tested;
public reads invoke zero inference; no private details in public snapshots;
revocation removes attribution from current snapshot and invalidates caches;
verified credit consumption and zero-subscription launch gate.

## Admission defense in depth
Local rolling budgets are defined in [ADMISSION_SECURITY.md](ADMISSION_SECURITY.md). Cloud request and polling limits must independently reject abuse before database and inference work. A member quota or global quota rejection must not be retried in a tight loop.

## SQL foundation
See [cloud mailbox core](CLOUD_MAILBOX.md) for the closed-by-default independent SQL schema and operations. HTTP routes, credentials and local reconciliation remain pending.

## HTTP core
See [authenticated gateway core](GATEWAY_CORE.md). Routes are implemented as an isolated Node handler, not deployed Netlify functions. Production adapters and distributed throttling remain prerequisites.

## Private transport
See [outbound bridge transport](BRIDGE_TRANSPORT.md). Typed client implemented but not running; local durable admission and approved outbox remain prerequisites.

## Activity observation cache — candidate cloud migration 008
The existing activity snapshot remains a 15-second live observation. A
60-second bridge cannot promise continuous live freshness. The separate
single-row cache accepts only a fresh (under 15s) DB-clock-checked sample
and fixed enum, rejects regression/conflicting replay, spaces distinct
writes at least 45s apart, and hides samples at 120s. Public presentation
must label it Last observed; it cannot trigger pajamas, sleep, work
admission or chat availability. No raw records, identifiers or free text.
Disabled by default; optional distinct projection writer/reader roles
have only their exact SECURITY DEFINER routine, with existing privilege
audit support. No roles provisioned, no migration applied outside tests.
The browser parser is isolated until the endpoint exists. Next is the
authenticated outbound publisher and read-only HTTP adapter with separate
credentials, explicit budget/edge controls and reviewed activation.
No automatic Netlify provisioning, deployment or additional spending.

## Authenticated activity transport candidate
Explicit private operator CLI: python -m penny.runtime.activity_publish
--config PRIVATE_PROJECTION_CONFIG --confirm (one invocation; no timer).
Config uses protected local penny DSN, approved Netlify hostname and separate
projection_key_hex (32–64 bytes). It sends only sample epoch and enum with
a domain-separated HMAC covering both, no bridge/member signing key.
The candidate HTTP adapter accepts POST /api/v1/bridge/activity and GET
/api/v1/activity, exact origin, no redirect, short sample age, distinct
writer/reader roles, fixed routines and mandatory injected admission gate.
Configuration defaults closed, production-only, separate credentials and
warm configuration pinning; no ambient DB credentials. Responses no-store
until edge/cache budget is verified. Uncertain publication is not retried
by the client. SQL still enforces monotonic, spaced writes and expiry.
No provider admission gate implementation, function entrypoint, deployed
DB role, publisher timer, browser fetch wiring or actual publication.
Manual invocations are not a persistent local attempt limiter; automated
publication requires durable cooldown and reviewed credit budget. Do not
activate before those gates, scoped role audit, HTTPS tests and Maker approval.
