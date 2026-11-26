# Member session foundation
## Objective and state
Migration 009 stores opaque session IDs, verified member UUID, SHA-256 digest
of a random 256-bit bearer token, issuance, expiry and optional revocation.
Only the trusted identity adapter issues tokens after external identity
verification; no public minting endpoint. Initial one-hour expiry and five
active sessions per member are provisional. Tokens are returned once, never
stored raw or logged.

## Flow
Trusted verified identity -> administrator Guardian issuance check -> random
token and digest stored under transaction lock. Token-only MemberMemoryService
accepts no member ID. Each operation resolves the token to its owner inside
the same locked transaction as consent or preference access, preventing
revocation races between lookup and mutation. Revocation marks the session
unusable; privacy withdrawal remains available during model identity failure
for an otherwise valid session. Owner scope and consent epoch remain separate.

## Limits
This is a session primitive and adapter, not an end-to-end login system.
External identity provider, member registry, password/MFA or federated login,
TLS, rate limiting, HTTP security, admin authentication, DB roles/RLS, session
cleanup and deployment are not implemented. Raw UUID repository functions
remain trusted internal-only. Bearer possession grants access until expiry or
revocation; no tokens in URLs, logs or Git. No personal recall integration yet.
Apply migrations 001–009. No actual user credentials were created.
