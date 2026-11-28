# Exact-draft reply release (private beta)
Migration 014 binds one explicit trusted operator approval to the exact
successful local draft hash, question receipt, pinned identity and reviewer.
Requires live lease, current enabled owner mapping, confirmed cloud ack,
successful local task and unpaused scheduler. The model and member cannot
authorize publication. Worker may retrieve only approved reply text and
fence; delivery receipt records confirmed remote acknowledgement. Modified
draft, identity mismatch, disabled account, expired lease and stale fence
fail closed. Confirmed delivery is idempotent. No generalized publish or
network capability granted. Review is a human attestation, not proof of
factual correctness. Runtime role isolation and operator authentication
still needed; no automatic content classifier or live deployment.
A check before an external call cannot make revocation and remote delivery
atomic; a future worker must recheck just before sending and handle in-flight
revocations and ambiguous outcomes explicitly. No network calls in this
repository layer. Next: orchestrate bounded claim/ack/release and recover
persistent pending actions, then end-to-end private beta with real runtime.
