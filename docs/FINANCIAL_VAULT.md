# Financial Vault v0.1 — recorded cash journal
Objective: record evidence-backed historical events, not spend funds.
Migration 018 defines immutable typed USD journal entries, fixed integer
cents, globally unique source references, source evidence hash/size,
reviewer, occurrence/record time and unique exact reversal link.
Each event produces two balanced signed postings through a fixed view.
No arbitrary account choice, founder withdrawal or transfer from Penny.
A trusted administrator records independently reviewed evidence; replay
returns same entry, conflicting source fails. Correction reverses exactly
once, then posts a new corrected event. Model/member cannot record entries.
Evidence bytes remain private outside Git; hash is integrity, not proof of
truth or independent reviewer authentication. Source refs must be opaque.
No payment connector, bank data, purchase authority or automatic spending.
Commercial receipts/refunds, community support, founder cash funding,
founder-paid actual costs, cash operating costs, payment fees and attributed
founder merchandise/entertainment income/costs are separate. Founder-paid
Penny expense debits Penny expense and credits contributed capital; it is
not fictitious debt or cash inflow. Do not enter founder contribution twice.
Cash entries track actual observed cash changes, not reconciled balances.
Negative recorded cash flags incomplete/inconsistent cash records; it does
not create debt or permission to spend. No real financial amounts seeded.
Summary reports unavailable when no entries exist; founder-only records
do not imply Penny's balance. Zeros within a recorded scope mean zero
recorded for that category, not verified complete history.
Commercial result is recorded net commercial receipts minus recorded costs,
not audited profit, tax result, net worth, available cash or approved
million-dollar mission metric. USD cash-only prototype; accrual accounting,
assets, liabilities, reserve/budget allocation, mixed revenue attribution,
reconciliation, payment-provider receipts and public projection remain
separate later gates. Founder ledger covers project-attributed records only,
not personal finances; cross-ledger contributions not consolidated here.
DB role isolation, externally authenticated operator, durable evidence store,
backup/restore and audit of actual costs required before real use.
No production data or deployment. Tests use synthetic cents only.
