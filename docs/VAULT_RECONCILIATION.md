# Manual cash reconciliation (v0.1)
A trusted administrator with independently verified evidence attests the
aggregate dedicated Penny USD cash scope, including complete opening
history, all cash accounts and no unrelated founder funds. No actual bank
connection or real financial records are used by this code.
Migration 019 stores an immutable snapshot with reference, evidence digest,
reviewer, statement cutoff, ledger cash/count and observed nonnegative cash.
An explicitly evidenced zero is valid; absence of a snapshot is unavailable.
Duplicate exact submission replays; conflicting reference fails. Older
statement cutoffs cannot supersede a newer snapshot. Mismatch is recorded
rather than hidden or corrected automatically. Founder-only income/costs
do not invalidate Penny's snapshot; any new Penny event does, including
noncash costs, backdated entries and reversals that net to zero.
The latest snapshot is matched only while its ledger count and cash agree,
the statement covers the latest occurrence, difference is zero and statement
age is less than 24 hours (provisional beta threshold). Otherwise report
unavailable, ledger_changed, mismatch or stale. Difference is historical,
not a comparison with current cash if ledger changed. No synthetic balance.
A match is historical cash confirmation by attestation, not independent
bank verification, available-to-spend cash, audited profit or permission
to spend. Actual liabilities, reserves, settlement holds, restricted funds,
coverage and administrator identity must be independently validated.
No external payment or spending capability. No public projection, live
admin UI or production deployment. Local privileged DB users can bypass
application rules; real role separation and backups remain launch gates.
