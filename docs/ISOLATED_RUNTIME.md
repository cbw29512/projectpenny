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
