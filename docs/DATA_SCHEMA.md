# Logical data schema v0.1
Proposed relational contract; not implemented DDL. UUID identifiers, UTC timestamps, explicit foreign keys, audited mutations.

| Entity | Fields and constraints |
|---|---|
| member | id, unique auth_subject, status, consent_version |
| entitlement | member_id, tier, valid_from, expires_at, verified source_event_id |
| payment_event | provider, external_id unique per provider, amount_minor, currency, verified_at, processing_state |
| conversation | id, member_id; owner-scoped |
| message | conversation_id, role, content, created_at, job_id; one final reply per job |
| work_task | id, member_id nullable, kind, queue_class, state, submitted_at, deadline, idempotency_key, tier_snapshot, attempt, lease_epoch, lease_until, checkpoint_id; unique requester/key |
| scheduler_control | singleton, active_task_id, mode, capacity_version, last_served_member |
| task_checkpoint | task_id, sequence, state_ref, created_at |
| task_outcome | unique task_id, status, evidence_ref, error_code, measured_usage |
| quota_usage | member_id, period, kind, count; atomic update |
| notification | member_id, task_id nullable, kind, consent, status, expiry, dedupe_key |
| memory_record | scope, member_id nullable, content_ref, provenance, confidence, validation_state, retention_until |
| opportunity | origin_insight_id, state, evidence_ref, cost_estimate |
| proposal | member_id, opportunity_id, content_ref, state |
| vote | proposal_id, member_id, choice; unique ballot/member |
| decision | evidence_refs, rationale, policy_version, approval_ref, outcome_ref |
| decision_influence | decision_id, proposal_id, explanation |
| identity_version | version, asset_hash, policy_hash, approved_at; read-only for AI |
| model_version | digest, config, benchmark_ref, approval_status |
| ledger_account | owner_scope, currency, type |
| journal_entry | source_ref unique within source, posted_at, status, reversal_of |
| journal_line | entry_id, account_id, debit_decimal, credit_decimal; balanced per currency |
| budget | period, cap_decimal, reserved_decimal, spent_decimal, approval_ref |
| spending_request | purpose, amount_decimal, status, approval_ref |
| compute_usage | task_id, model_version, tokens, wall_time, cost_estimate, reconciliation_ref |
| milestone | metric, threshold, verified_at, evidence_ref, world_asset_version |
| audit_event | actor, action, entity_ref, correlation_id, timestamp; append-only |

## Transitions
Task: submitted -> queued -> running -> succeeded/failed/canceled/expired. Running -> checkpointed -> queued only with reserved bounded capacity. Leases and fencing reject stale workers; external effects require idempotency and reconciliation.
Memory: candidate -> quarantined -> validated -> approved -> active -> superseded/revoked. Consent and deletion rules override recall.
Opportunity: received -> researching -> evaluated -> proposed -> approved/rejected -> implemented -> measured. Attribution opt-in.
Payment: received -> verified -> applied -> reconciled; verified refunds/reversals adjust entitlements.
Accounting: use fixed precision decimals, balanced entries and reversals. Separate commercial receipts, support, memberships, founder funds, costs, assets and liabilities. Publish net earned cash, available cash, accounting profit and net worth distinctly. Never double-count prepaid credits or transfers.
