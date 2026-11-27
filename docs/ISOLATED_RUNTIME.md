# Dedicated NucBox service isolation — candidate only

## State and trust boundaries
Three distinct system accounts and primary groups (non-login, no supplementary
privileged groups), never the Maker's SSH user. Each reads its own config,
root-owned code and dependencies; other configs and home directories are
inaccessible. No model runs under the bridge account. Ollama remains a
separate local service. Operator controls are trusted local SSH only.

| Service account | Config directory | Network |
| --- | --- | --- |
| penny-infer | /etc/penny-private/inference | IPv4 loopback only |
| penny-bridge | /etc/penny-private/bridge | Local DB and approved public HTTPS |
| penny-project | /etc/penny-private/projection | Local DB and approved public HTTPS |

The fixed config filenames are inference.json, bridge.json and projection.json.
Root-controlled /etc/penny-private parent, each immediate config directory
owned by its corresponding account, mode 0700; config file owner same, 0600.
Keep operator credentials elsewhere (Maker home or private operator directory),
never in worker files or environment. Each DSN must use a separate restricted
database principal, not an owner, superuser or shared operator login. This
change does not provision or certify those privileges.

Root-owned /opt/penny/release and /opt/penny/venv must be traversable/readable
but never writable by workers, including every ancestor, symlink target and
Python base interpreter. Do not reuse the existing home-based venv: its
interpreter may point into /home and ProtectHome hides it. Rebuild a verified
venv under /opt using a trusted system interpreter and pinned dependencies
in a later explicit deployment. No secret or writable checkout in the release.

## Candidate system units
deployment/isolated/ contains separate, non-installed SYSTEM units with distinct
names from existing user units. Use system-level systemd (not --user) because
privileged manager namespace/identity controls must actually be enforced.
Read-only filesystem, private temp/device view, hidden home/process access,
empty capabilities, no privilege escalation, no core dumps, bounded tasks,
native syscall architecture, restricted address families, explicit bind
denial, management socket exclusions and inference IP loopback restriction.
See https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
and https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html.

IPAddress rules are address-based, not port-based. Inference still can reach
other loopback TCP services; Unix-domain sockets and abstract sockets need
independent policy. Bridge/project application validation is not an OS egress
allowlist: enforce outbound destination/port policy separately before enabling.
Systemd BPF/namespace features may be unsupported or ineffective on some
hosts. Verify actual enforcement, not just parsed settings. Bind restrictions
do not prove no inherited sockets or other IPC. PrivateTmp permits temporary
writes; read-only mount restrictions are not a substitute for DAC/ACL checks.
No complete sandbox or zero-trust certification claim.

## Acceptance and cutover (no automatic installer)
1. Verify current release and CI; inspect active/installed legacy user units,
   protected DB gates and backup/restore. Never run both timer generations.
2. Provision system identities, protected config paths and audited separate
   database principals; verify no sudo/docker/administrative group access.
3. Verify systemd-analyze verify against prepared candidate files on NucBox,
   then inspect systemd-analyze security and actual denied operations in an
   isolated rehearsal. Validate access to only intended files and endpoints;
   deliberately check denial of cross-account configs, writes, listen sockets,
   non-loopback inference and privileged local sockets. Never expose secrets.
4. Stop only legacy Penny timers/services and close durable DB gates. Verify
   no in-flight model work; use existing reviewed recovery if required.
5. Only after separate authorization install candidate system units, with
   timers disabled; test each oneshot with gates closed then authorized
   bounded rehearsal. Verify emergency stop stops system rather than user
   units. Enable timers only after all acceptance and operator approval.
6. On failure close gates, stop isolated units, verify actual inference
   stopped and restore known-good legacy release/config under review. Never
   automatically restart old timers or clear uncertainty.

No actual users, paths, permissions, units, database grants, firewall rules,
SSH settings or running services modified by this repository change.

## First local database scope: activity publisher
Migration 041 moves reservation, outcome recording and coarse activity inputs
behind three SECURITY DEFINER routines, each with pinned search_path and no
PUBLIC execute. The worker uses these fixed calls instead of scheduler/task
or delivery-control table access. The existing Maker-only configure/recover
operations still require separate local operator credentials, never the
publisher role. Use a fresh restricted login with schema USAGE and EXECUTE
on penny_activity_reserve(text), penny_activity_finish(text) and
penny_activity_inputs() only. No table/column/sequence grants, ownership,
role membership, CREATE, elevated flags or grant option. Provision and audit
with a trusted DB operator; migration grants no runtime role automatically.
Dedicated non-login trusted function owner required; verify actual effective
privileges, search paths, other schemas and default grants. Existing broad
roles must not be reused. The routines enforce durable attempt cap/cooldown
and cannot enable publication or change approved limits. A compromised
publisher could misreport public observations or exhaust its approved budget;
no assertion of authenticity after key theft. Inference and mailbox scopes
still require deeper refactoring. No live migration or role changes.

## Mailbox reply boundary (partial)
Migration 042 limits delivery to two fixed routines: penny_bridge_pending_reply(uuid)
and penny_bridge_record_delivery(uuid,uuid,text). Both pin search_path and
revoke PUBLIC execute. The private invoker helper must NOT be granted to
workers. Only acknowledged, unexpired, mapped, successful, exact SHA-256
reviewed replies with the pinned identity can be read. The trusted Maker's
approval remains separate. Receipt recording cannot change approval, text,
identity or fence. A compromised delivery credential can falsely attest
receipt or disclose previously approved replies; remote receipt truth still
requires reconciliation. No production grants are installed. A fresh delivery
role may be tested with schema USAGE and only these two EXECUTE grants.
Full mailbox worker is NOT ready for that role: admission, scheduling,
acknowledgement and rejection still use direct table queries and must be
scoped before deployment. Do not grant broad access as a workaround.

## Mailbox visitor admission and acknowledgement (migration 043)
Worker calls penny_bridge_admit(uuid,uuid,uuid,bigint,text) and
penny_bridge_ack(uuid,uuid,uuid) instead of direct receipt/task/mapping SQL.
Both revoke PUBLIC execution and pin search_path. The new admission routine
requires enabled/unblocked bridge and unpaused scheduler, locks the same
scheduler row, computes exact payload digest in PostgreSQL, verifies mapped
member, bounded lease, exact replay, durable receipt cap, local entitlement,
rest schedule, queue caps and rolling member/community quotas. It creates
only mapped visitor tasks and no recall scope. Direct legacy tests now
explicitly enable the bridge, as the production worker already requires.
The SQL policy mirrors the existing Python admission thresholds; maintain
parity when changing them, and require disposable PostgreSQL parity and
concurrency tests before release. PostgreSQL and Python Unicode whitespace
and timezone versions require boundary testing. A compromised bridge or cloud
credential can submit invented questions for already mapped owners; the
mapping alone does not prove end-user intent. Existing approval/review and
external authentication remain mandatory. Ack only records a fenced
attestation; it is not proof of remote delivery. Worker scheduling, deferral
and rejection still require scoping before the full worker can use an
EXECUTE-only role. No production role grants, migrations or service changes.

## Mailbox worker SQL boundary (migration 044)
The complete runtime bridge path now calls seven fixed routines: admit, ack,
pending_reply, record_delivery, reserve, defer and reject, with signatures in
migrations 042–044 and tests/test_mailbox_role.py. No direct table access is
needed by the supported worker path; session advisory locks remain standard
PostgreSQL calls. Reserve enforces durable cooldown, bridge/scheduler gates,
expiry housekeeping and rest; defer only extends cooldown and latches a block;
reject only marks a matching failed/expired/canceled mapped receipt. The
private rest helper and reviewed-reply helper must never be granted to workers.
Full restricted-role roundtrip and negative tests are added, not certified.
The role can still consume resources, attest false receipts or send arbitrary
requests using a stolen cloud credential; external auth, network egress and
provider quotas remain separate boundaries. Database routines do not prove
remote user intent or remote delivery. Provision a fresh dedicated login with
schema USAGE and only the seven EXECUTE grants, no table grants; audit PUBLIC,
ownership, membership and all other effective privileges before use. SQL rest
and admission policy parity remains a release gate. No actual production role
created or grants/migrations applied.

## Inference supervisor scope (migration 045)
The supervisor reserves a durable per-cycle UUID before model work and
finishes only that exact cycle. Missing, stale or consumed tokens cannot
clear the marker; active tasks prevent a clean finish. Maker recovery
invalidates the token. Two fixed SECURITY DEFINER routines with pinned
search_path and no PUBLIC execute replace direct supervisor gate writes.
Existing uncertain state is preserved. No role provisioning or migration
applied to production. This is not a proof of upstream model idleness:
a compromised supervisor can misattest its own outcome. Claim, recall,
completion and artifact intake still need scoping before a complete
EXECUTE-only inference role is possible. The child now receives an explicit
minimal environment and ignores Python environment/user site configuration;
this reduces accidental credential inheritance but does not isolate same-UID
files, /proc or memory and does not constitute a sandbox. The parent validates
bounded child JSON text. No change to canonical identity or model settings.

## Inference claim scope (migration 046)
Supervised inference now uses a claim-only repository with one fixed routine,
penny_inference_claim(uuid). It requires the current durable cycle token,
consumes a single claim attempt (including idle), checks gates and rest,
expires old tasks, cancels changed entitlements and selects only one task.
It returns that task's fenced payload and memory flags, never the full queue.
The SQL selection mirrors the approved Python policy: aged-first, last-member
avoidance, exact 60/30/10 usage normalization, tier and deterministic arrival.
Parity tests and restricted-role denial tests are required before release.
The old trusted local TaskStore remains for operator/test workflows; do not
run both dispatch paths concurrently. Claim access alone is not authority to
recall memory or complete a task. Those operations still require scoping.
The inference runtime role is NOT yet ready for execute-only deployment.
No role grants, live migrations or service changes were made.

## Personal recall scope (migration 047)
The supervised worker calls penny_inference_personal_recall(uuid,uuid,uuid)
using the current cycle, task and fence. The database derives the owner and
consent epoch from the live task; no arbitrary member lookup or text search.
Only an unexpired enabled consent of the approved version may return up to
three latest preferences. A one-shot content-free attempt marker covers
empty or stale-consent results. Existing snapshot IDs are committed before
return; completion still uses its existing consent/deletion recheck.
No direct personal memory or consent grants are needed for this operation.
Legacy trusted recall is retained for local/test workflows, not the supervised
worker. Existing Python completion and business recall are still unscoped.
Do not deploy an execute-only inference role until those are addressed.
No production grants or migration applied; CI and privacy-race rehearsal pending.

## Business recall scope (migration 048)
The supervised worker calls penny_inference_business_recall(uuid,uuid,uuid)
with current cycle/task/fence. Only live explicitly memory-informed internal
work can read reviewed, unrevoked, unexpired business records. Search derives
from stored task text (maintenance topic only); no arbitrary query parameter.
Bounded 32 lexical terms, 24 ranked candidates inside SQL, at most 3 full
records/1500 characters returned. Source audit committed with the result;
empty recall is recorded and consumes the one permitted attempt. No raw
memory-table grants or memory approval authority. SQL rank version is
english-lexical-v2-sql: PostgreSQL lower/whitespace semantics may differ from
Python Unicode casefold/split, so Unicode and ranking parity require testing.
Trusted local recall remains separate. Completion and candidate intake still
need isolation before full EXECUTE-only inference deployment. No live migration,
role changes or production certification.

## Ordinary draft completion (migration 049)
The supervised worker now uses penny_inference_complete_draft(uuid,uuid,uuid,text)
for ordinary results, bound to current cycle/task/fence and unexpired lease.
The routine writes only a fenced outcome and scheduler accounting, rejects
replay, and checks consent/deleted preference snapshots before retaining
text. PUBLIC execute is revoked; no production grants installed. Specialized
internal memory-review, maintenance, business-draft and workshop tasks return
an explicit specialized status without storing anything. The current runtime
opts into the existing trusted Python completion for those routes only, to
preserve atomic candidate validation and staging. The adapter defaults to
refusing specialized completion, and never falls back after a refusal or
uncertain database result. This transitional runtime still needs legacy
privileges for specialized tasks; do not provision a broad worker role or
certify the inference boundary yet. Next scope those four intake routes.
No production migration, role changes or live deployment. CI remains pending.

## Learning-candidate completion (migration 050)
The existing scoped completion routine now handles memory-review tasks without
legacy table privileges. A private SQL parser retains JSON duplicate-key
rejection, exact fields, allowed kinds, Python-compatible trim characters and
content limits. Invalid model proposals still record the bounded raw outcome
but stage no candidate, matching the existing Python path. Valid proposals
and source outcomes commit together; no approval or evidence authority is
added. The parser has no PUBLIC execute grant and must not be granted to
runtime roles. Tests cover parser parity, restricted-role staging and atomic
rollback; PostgreSQL behavior is not yet certified. Maintenance proposals,
business drafts and Workshop artifacts still use the explicit transitional
legacy path. No production migration, role grants or deployment performed.
