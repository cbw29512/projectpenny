# Relevance-ranked private memory

## Objective / acceptance
Retrieve relevant approved business memories for an explicitly memory-informed,
live internal claim. Older relevant records beat unrelated newer ones. No match
means no memory, not unrelated fallback. Member and ordinary internal jobs
cannot recall. Audit the exact returned source IDs in the same transaction.

## State
Migration 004 adds a partial GIN index on the English text-search vector and
recall event/source tables. Event records task, fence, timestamp, policy/rank
version and count; source rows record returned memory UUID and position.
No private text is copied into audit. These tables need role-level append-only
permissions in production. The event represents retrieval, not proof of model use.

## Logic
Guardian -> verify stored task, fence, lease, internal owner and explicit purpose
-> normalize up to 32 plain search terms from stored task payload -> parameterized
PostgreSQL English OR query -> rank by lexical match, recency and UUID -> bounded
24 candidate pool -> suppress case/whitespace-normalized duplicates -> select
at most 3 whole records / 1500 content characters -> transactional audit -> return.
No semantic embeddings, additional model calls or external dependencies.
Audit failures roll back and stop worker execution through its existing boundary.

## Limitations
English lexical matching may miss synonyms, multilingual text and implicit context;
pool and limits are provisional. Duplicate suppression is recall-time only.
Quarantined correction/consolidation proposals are supported via [maintenance](MEMORY_MAINTENANCE.md); no verified contradiction detection or automatic application. Audit records
allowed retrievals, not denied attempts, and does not prove inference completion.
No automatic public access, trusted approval or production deployment.
