# Trusted local operator controls (SSH)
Migration 017 records successful runtime changes with local UID and database
time. The operator CLI uses its own private operator.json containing only
the dedicated loopback penny DSN. Local OS access and trusted DB permissions
are the authentication boundary; do not expose this CLI or database role to
the model, browser or gateway. DB privilege separation and OS isolation
remain deployment gates.

After a verified local installation, invoke from the release directory:
    python -m penny.runtime.operator --config ~/.config/penny/operator.json status
    python -m penny.runtime.operator --config ~/.config/penny/operator.json stop
    python -m penny.runtime.operator --config ~/.config/penny/operator.json start inference --confirm
    python -m penny.runtime.operator --config ~/.config/penny/operator.json start bridge --confirm

Stop atomically closes both DB gates and pauses admission even during
identity drift. It does not kill in-flight work or systemd timers. For an
emergency stop, stop only Penny's two timers/services via systemctl --user,
close DB gates, then verify the upstream inference actually ended. Never
stop shared Ollama or other existing services automatically.

Inference recovery requires both gates closed, scheduler paused, a sticky
uncertainty marker, no held inference service lock, and explicit operator
confirmation that the previous inference has stopped. If a task remains
running, status supplies its exact task ID and fence; its lease must have
expired. Run recover-inference --confirmed-isolated with --task-id and
--fence only when a running task is reported. No active task permits the
same command without IDs. Neither form restarts work. Bridge recovery
requires review of the remote outcome and credentials, then
clear-bridge-block --confirmed-reviewed; preserves cooldown and disabled
state. Restarting either gate is a separate explicit action. Commands are
not proof of isolation, provider readiness or remote reconciliation.

No UI network listener or service installation. Review and approval UI,
readiness checks, actual runtime credentials, deployment, backups and
model certification still required. No new expenditure.
