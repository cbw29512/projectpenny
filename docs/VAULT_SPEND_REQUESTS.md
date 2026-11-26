# Nonbinding spending requests
Migration 020: immutable quote request and terminal rejection record.
Trusted administrator stages evidence-backed typed USD quotes, exact
idempotency, maximum seven-day expiry, bounded categories and amounts.
Pending -> rejected or expired; no approval transition yet. All statuses
return zero authorized and reserved cents. Guardian SPEND remains denied
for every actor. No payment, binding order, external tool or model access.
Next: separate budget/reserve policy and atomic approval against fresh
reconciliation, verified liabilities/holds and explicit owner authorization.
Do not infer approval from a quote, a matching cash balance or this PR.
No live data or deployment.