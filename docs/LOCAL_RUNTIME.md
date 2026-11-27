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
