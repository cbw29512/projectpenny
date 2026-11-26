# Explicit member memory consent and ownership
## Objective / state
Migration 008 separates member preferences from business learning, entitlements
and recognition. Consent defaults off, with explicit accepted version, epoch,
grant/expiry and enabled state. Preferences have composite owner/ID keys and
a composite FK to the current owner consent epoch. Consent events contain no
preference text. Initial policy: 90 days and at most 20 preferences of 300 chars
per member. These are provisional limits, not legal retention advice.

## Flow
Trusted authenticated member adapter derives member ID from session (not client
input). Explicit opt-in creates a consent epoch; repeated active opt-in does
not extend expiry. Explicit save checks current owner, epoch and quota under
shared transaction lock. Owner list returns only active consent records.
Withdrawal deletes live preference rows and disables consent atomically with
audit. Re-opt-in or renewal after expiry starts empty with a new epoch.
Individual owner deletion and consent withdrawal are available even if identity
integrity fails: privacy controls cannot depend on model availability.

## Limits
The raw repository is internal-only. The token-only adapter is described in
[MEMBER_SESSION.md](MEMBER_SESSION.md). Upstream identity verification, database
roles/RLS, consent UI and production isolation remain pending. No automatic extraction from conversations,
no model recall, public recognition or supporter-tier effects. Preference text
is untrusted; sensitive data/credentials must not be admitted by the future UI,
and content filtering is not yet implemented. No claim of complete erasure:
expired rows are inaccessible but remain until withdrawal or renewal, and
backups/WAL and other copies need their own retention process. No personal data
was collected or migrated. Apply migrations 001–009 in order.
