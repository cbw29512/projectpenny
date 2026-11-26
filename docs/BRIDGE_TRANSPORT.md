# Outbound NucBox transport — not a running service
Objective: trusted Python connector exchanges narrow mailbox messages
without listening on any port or exposing transport to the language model.
State: RemoteClaim holds question UUID, cloud owner UUID, fence, lease UTC,
bounded text; BridgeResult distinguishes empty, claimed, ok, conflict,
unauthorized, backoff and uncertain. No persistent admission or outbox yet.
Logic: operator configures one Netlify subdomain and independent 32-byte
or stronger bridge HMAC key -> five-minute scoped credential -> verified
TLS HTTPS POST -> fixed endpoint -> bounded response and strict field
validation. No redirect following, proxy configuration, arbitrary URL,
compression, inbound listener or automatic retry. Unknown fields, expired
claims, excessive leases and malformed responses rejected. Do not trust
cloud owner as local identity: future local allowlist maps approved users.
Upload failures may be ambiguous; explicit durable reconciliation required.
Honor Retry-After with conservative floor; no tight polling. Socket timeout
is not a hard whole-operation deadline; supervisor isolation/deadline and
OS egress allowlist must be added before use. Default TLS trust and hostname
verification do not independently prevent DNS rebinding; operator-controlled
hostname, network policy and approved deployment are mandatory.
No keys in Git, no live host configured, no real requests in tests.
Transport is not permission to publish arbitrary model text. Local admission,
owner mapping, durable receipts/outbox, independently approved release,
runtime isolation, provider edge controls and credit measurement are next.
