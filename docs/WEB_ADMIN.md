# Maker administration — NucBox only (supersedes former web-admin design)
Owner decision: every Penny administrative action and management interface
must run on the private NucBox. The cloud is an untrusted public delivery
layer, not a control plane. No public /admin page, cloud administrator login,
admin HTTP function, remote command queue, inbound listener, port forward,
reverse tunnel or cloud-issued local control credential. No remote
authorization of products, memory, spending, identity, model or services.

The only approved management access is direct local NucBox access or SSH
from the Maker's designated desktop on the trusted local network. Prefer
the existing SSH CLI or an SSH terminal dashboard; no management web listener
is required. No WAN SSH, router forwarding, reverse tunnel, cloud relay or
shared remote-access credentials. A future loopback-only web UI and any SSH
local forwarding require separate explicit approval; do not enable either
by default. Use a dedicated desktop SSH key, non-root login, least-privilege
operator account and host-key verification. Restrict SSH to the approved
LAN interface and desktop address (verify both before choosing rules).
Firewall and sshd policy are deployment gates: verify a recovery path and
an independent authorized session before any restrictive change. Do not
modify the existing SSH service, firewall, accounts or keys automatically.
No assumed address, no existing configuration certification.

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
