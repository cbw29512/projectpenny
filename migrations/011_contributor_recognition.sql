BEGIN;
-- Evidence-backed outcomes are distinct from member attribution.
CREATE TABLE contribution_outcome (
    id uuid PRIMARY KEY,
    outcome_ref text NOT NULL UNIQUE CHECK (length(outcome_ref) BETWEEN 1 AND 128),
    verdict text NOT NULL CHECK (verdict IN ('improved','unsuccessful','inconclusive')),
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
    evidence_size integer NOT NULL CHECK (evidence_size BETWEEN 1 AND 16384),
    reviewer_id uuid NOT NULL,
    recorded_at bigint NOT NULL,
    policy_version text NOT NULL
);
-- Explicit owner opt-in, scoped to one outcome and role. New consent gets a new ID.
CREATE TABLE contribution_request (
    id uuid PRIMARY KEY,
    member_id uuid NOT NULL,
    outcome_id uuid NOT NULL REFERENCES contribution_outcome(id),
    role text NOT NULL CHECK (role IN ('idea','testing','bug_report','advice')),
    consent_version text NOT NULL,
    requested_at bigint NOT NULL,
    UNIQUE (member_id,outcome_id,role)
);
-- A private recognition event exists only following independent evidence review.
-- Owner withdrawal removes this live attribution, but not the nonpersonal outcome.
CREATE TABLE contribution_recognition (
    request_id uuid PRIMARY KEY REFERENCES contribution_request(id) ON DELETE CASCADE,
    evidence_ref text NOT NULL CHECK (length(evidence_ref) BETWEEN 1 AND 128),
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[a-f0-9]{64}$'),
    evidence_size integer NOT NULL CHECK (evidence_size BETWEEN 1 AND 16384),
    reviewer_id uuid NOT NULL,
    recorded_at bigint NOT NULL,
    policy_version text NOT NULL
);
CREATE INDEX contribution_request_owner ON contribution_request(member_id,requested_at,id);
COMMIT;
