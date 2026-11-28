# Fenced personal context
## Objective and state
Migration 010 binds an explicit opt-in private task to its authenticated member
and current consent epoch. A bounded snapshot stores up to three preference
IDs and fence, never preference text. No preference FK prevents owner deletion.
No consent by default and no personal context for ordinary or business tasks.

## Flow
Token-only chat service resolves owner during scheduler admission -> explicit
memory flag checks active consent -> atomic task and scope insert -> worker
checks live fence, stored owner, active epoch and pause -> newest three
preferences -> separate user-role personal context envelope -> private draft
completion rechecks epoch and recalled IDs under lock. If withdrawn, expired
or deleted after recall, cancel and discard the successful result. A stale
epoch before recall yields ordinary context. No business context mixing.
Idempotency key binds payload and consent epoch. No session credential stored
with the task. Accepted jobs may run after session expiry; current consent
is independently enforced.

## Limits
Only preference records explicitly saved by a member, no automatic extraction.
Preference text remains untrusted; semantic safety not guaranteed. Already
running inference cannot be recalled; previously completed results may contain
derived data and need separate retention/deletion policy. No public reply
delivery, identity-provider integration, DB role isolation or live GPU test.
Three-record bound and newest-first selection are provisional. Apply migrations
001–010. No production data or spending.
