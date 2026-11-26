# Controlled business memory maintenance
## Objective and state
Penny may propose a correction, consolidation, outdated flag or contradiction
for reviewed memories. Migration 005 adds a quarantined proposal and linked
source IDs, not authority to mutate the approved memory table. One proposal
per fenced successful internal maintenance job. Correct/outdated reference one
source; consolidation/contradiction reference two or three distinct sources.
Only correct/consolidate have a replacement draft. Rationale max 500 chars,
replacement max 1000 chars. Policy version and creation time are stored.

## Flow
Trusted internal caller submits explicit maintenance job -> existing exclusive
worker recalls reviewed records -> model outputs structured proposal -> strict
parser and separate Guardian capability -> fenced outcome transaction checks
all sources were retrieved together under the same task/fence and are still
active -> quarantine proposal and source links atomically. Denied or malformed
proposal remains only a private draft. Storage errors roll back completion.
No model permissions to approve, revoke, merge, delete or alter identity.

## Limits
Apply migrations 001–005 in order. This is proposal intake only, not unattended
maintenance scheduling or administrator adjudication. Contradiction detection
is a model suggestion, not verified fact. No semantic guarantee, no retention
purge, no new external actions. Lexical recall can miss useful records and
duplicate suppression may hide near-identical candidates. Reviewer UI,
independent evidence and atomic application of accepted proposals remain
pending. Internal task admission must be authenticated and isolated in deployment.
