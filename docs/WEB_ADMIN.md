# Maker administration — NucBox only (supersedes former web-admin design)
Owner decision: every Penny administrative action and management interface
must run on the private NucBox. The cloud is an untrusted public delivery
layer, not a control plane. No public /admin page, cloud administrator login,
admin HTTP function, remote command queue, inbound listener, port forward,
reverse tunnel or cloud-issued local control credential. No remote
authorization of products, memory, spending, identity, model or services.

Use existing trusted SSH operator commands and private local database.
A future convenience dashboard must bind to loopback only and be accessed
through an explicitly established trusted SSH session (no public exposure).
Local OS identity and separate least-privilege operator credentials remain
the trust boundary. No automatic installation or service changes.

Cloud roles remain limited to public member mailbox, outbound bridge,
maintenance and isolated reviewed projection reads/writes. No admin
runtime role. Cloud migrations 006/007 remain historical; corrective
migration 009 disables former admin identities, drops callable admin
routines and preserves audit rows. Never provision legacy admin roles or
credentials. Audit actual existing roles and remove legacy grants/credentials
if any were ever provisioned, using approved operator-only maintenance.
No production environment has been verified or changed here.

Emergency stop is local: close private admission/inference/bridge/activity
gates and stop only Penny's units. A disconnected cloud may still accept
bounded mailbox requests until its own admission/expiry policy closes them;
no local action is executed. Hosting admission configuration is a trusted
operator provisioning/maintenance concern, not a public API. An approved
outbound-only availability lease is a future improvement, not a remote
admin command channel. No cloud access to NucBox.

## Defense in depth
Public-only IPv4 HTTPS is shared by both outbound connectors. No DNS
fallback to internal/private ranges; original hostname TLS validation.
Still require separate OS service identities, protected release ownership,
local firewall/egress policy, database role audit, SSH key-only access,
verified backup/restore, and adversarial rehearsal before production.
