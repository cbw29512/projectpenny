# Offline personality regression framework
## Objective / state
Preserve Penny's permanent character while improving knowledge and model
capabilities. The versioned suite defines eighteen synthetic situations, three
human-review criteria each, two observations per case (36 total).
EvidenceRun binds model artifact and configuration digests, canonical identity
and suite digests, and ordered responses. Review binds an evidence digest,
reviewer UUID, every criterion verdict and reviewer notes.

## Flow
Trusted operator confirms isolated inference, exact artifact/configuration
and canonical identity -> offline capture using the supplied brain adapter ->
complete bounded evidence -> independent human review of all 108 criterion verdicts ->
fail-closed eligibility gate for baseline and candidate. Both must pass every
criterion; changed evidence, incomplete/reordered observations, altered identity
or suite, and failed or missing criteria deny eligibility. No keyword-only
judgment, model self-certification, payment or automatic model activation.
A failed or ambiguous inference stops capture without automatic retry.

## Scope / limitations
All current automated tests use synthetic or mocked outputs and certify the
framework only, not real model personality. No actual GPU run performed.
Model/config digests and isolation are operator attestations, not verified
runtime provenance. Reviewer UUID and verdicts are trusted internal inputs,
not authenticated approvals or signed evidence. The comparison requires a
different manifest and successful reviews; it does not quantify style drift
or guarantee future behavior. Evidence persistence, authenticated review,
independent paired comparison, actual model digest verification, activation
and rollback orchestration remain pending. Never run capture with the live
worker or expose it to public requests. No member data in fixtures.
