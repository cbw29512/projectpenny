# Supervised NucBox runtime — candidate units, not installed
Two independent systemd user timers run bounded oneshot services; no inbound
listener, no root installer and no changes to existing Ollama, Frigate,
Hermes or other services. Inference timer uses 15s after completion; bridge
60s after completion plus persistent DB cooldown. Hard service start
timeouts 120s/45s terminate the local service process group, not Ollama.
Migration 016 defaults inference disabled, records uncertain before invoking
the model, clears only after safe completion and no active lease. Crash or
ambiguous failure leaves sticky block; verify old inference actually stopped
before explicit operator recovery. Existing running work is never stolen.
Bridge independently starts disabled with its own sticky gate.
Config is a private regular file owned by runtime uid, no group/world access,
max 8192 bytes, no symlink. Separate inference.json and bridge.json; only
bridge file holds bridge key. DSN explicit loopback host and dedicated penny
database; actual separate least-privilege accounts still to provision.
Candidate paths: ~/.local/share/penny/release and ~/.local/share/penny/venv;
~/.config/penny/{inference,bridge}.json. No actual secrets or paths created.
Operator must install verified release and dependencies, run migrations,
configure secrets/DB roles, verify systemd unit compatibility and user
lingering, confirm Ollama model and resource isolation, and enable timers
only after approved checks. Do not run existing services under these units.
Emergency stop (only after installation): systemctl --user stop
penny-inference.timer penny-bridge.timer penny-inference.service penny-bridge.service
then close both DB gates and scheduler admission; a stopped process does
not prove upstream generation stopped. No automatic clearing of uncertainty.
User-unit process limits are not full sandboxing. Separate OS identities,
read-only release ownership, egress policy, secret isolation, model digest
certification, backups, restart drill and Netlify credit/edge checks remain
launch prerequisites. No public API, production installation or expenditure.

## Read-only readiness diagnostic
From the checked-out release with its Python dependencies, run:
    python -m penny.runtime.preflight_cli
Checks independent private config parsing, operator DB runtime schema
sentinels and gates, canonical identity, Ollama GET /api/tags inventory,
and fixed Penny systemd user unit states. No model generation/download,
service restart, database writes, secrets or remote communication.
Output never certifies readiness; model digest approval, actual runtime
role permissions, full migrations, performance, backups and live service
rehearsal remain separate checks. A diagnostic exit 0 means collection
completed, not that all checks passed. See https://docs.ollama.com/api/tags.

## Activity delivery candidate
Migration 040 defaults disabled. Separate penny-activity.service/timer candidate
uses the same durable gate as manual invocation, one attempt per 60 seconds
minimum, explicit operator-selected daily cap 1–1440 (UTC buckets; counts
attempts, not credits), endpoint/key binding and separate session advisory
lock. Reserve before HTTP; never refund a failed attempt. A lost process
leaves interrupted state until reviewed recovery; failures disable delivery,
and HTTP backoff preserves a 24-hour cooldown. Emergency stop disables the
activity gate too; restarting inference does not enable it. An already sent
request cannot be canceled by database stop. Stop the activity timer/service
as part of emergency procedure. Explicit --mode enable --daily-limit N
--confirm is required, using protected projection config. --mode disable
--confirm closes it; --mode recover --confirm reconciles interrupted state
without reopening. No units installed, migration applied, or cap selected
for production. Validate actual credit budget, permissions and endpoint first.

## Authorized management access
Direct local NucBox access or trusted LAN SSH from the Maker's designated
desktop only. Prefer SSH CLI/terminal UI rather than another listener.
No WAN SSH or router forwarding, cloud admin or remote tunnel. Actual LAN
interface, desktop address, key-only non-root access, host-key verification
and firewall/sshd effective policy must be verified before release. Do not
change live SSH/firewall rules without separate approval and a tested
recovery path; preserve the existing access and unrelated services.

## Read-only local security inspection
From the verified release, run python -m penny.runtime.security_audit_cli
for TCP listener classification. To inspect candidate sshd policy for the
approved desktop, additionally supply --user USER --desktop-ip LAN_IP
--server-ip LAN_IP --desktop-host HOST --ssh-port PORT. Do not infer approval
from SSH_CONNECTION. Add --protected-port PORT for each additional Penny
service. Default protected ports 5432 and 11434 are conservative candidates,
not proof of process ownership. No sudo, firewall change, key access,
network request, service reload or automatic remediation. sshd -T may fail
without sufficient permissions; unavailable is not a pass. This inspects
on-disk effective configuration for the supplied context, not the running
daemon or every Match context. TCP bindings do not prove network reachability;
Docker forwarding, other namespaces, UDP, router, firewall, source address
restriction, host key and actual running config require separate review.
Output omits raw addresses and configuration; keep results private.
References: https://man.openbsd.org/sshd.8 and https://man7.org/linux/man-pages/man8/ss.8.html
