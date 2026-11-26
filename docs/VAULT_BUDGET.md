# Nonbinding budget and reserves
Migration 021 adds append-only administrator budget reviews, holds and
explicit releases. Default planning capacity is zero. A review explicitly
attests owner consent, complete obligations/settlement holds/restricted
cash and retained reserve, binds the latest fresh matching reconciliation
and expires no later than that statement's 24-hour freshness limit.
Capacity = max(0, min(review ceiling, matched cash - reviewed obligations
- retained reserve) - all unreleased quote holds). This is a provisional
planning ceiling, NOT payment authorization, available bank cash or a
periodic spending budget. A zero ceiling closes new holds; stale or
changed reconciliation closes new holds. Existing holds persist across
expiry, ledger updates and budget changes until explicit evidence-backed
confirmation no external commitment exists. Reserve exact reviewed quote
amount/hash and current budget ID; scheduler transaction serializes
concurrent holds; rejection and reservation are mutually exclusive through
trusted application functions. Released quotes are terminal. No automatic
payment, order, recurring obligation, founder withdrawal or spending.
Guardian SPEND remains denied to every actor. No live financial records or
positive budget created outside disposable test fixtures. Actual operator
authentication, DB isolation, approval/revocation UX, independently reviewed
obligations and owner policy, transaction settlement/cost tracking and
reconciliation of real funds remain gates. No execution permission.
