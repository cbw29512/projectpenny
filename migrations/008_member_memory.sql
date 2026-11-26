BEGIN;
-- Separate from business memory and entitlements. No default opt-in.
CREATE TABLE member_memory_consent (
    member_id uuid PRIMARY KEY,
    epoch uuid NOT NULL,
    enabled boolean NOT NULL,
    policy_version text NOT NULL,
    granted_at bigint NOT NULL,
    expires_at bigint NOT NULL CHECK (expires_at > granted_at),
    UNIQUE (member_id,epoch)
);
CREATE TABLE member_memory (
    member_id uuid NOT NULL,
    epoch uuid NOT NULL,
    id uuid NOT NULL,
    preference text NOT NULL CHECK (length(preference) BETWEEN 1 AND 300),
    created_at bigint NOT NULL,
    PRIMARY KEY (member_id,id),
    FOREIGN KEY (member_id,epoch) REFERENCES member_memory_consent(member_id,epoch)
);
CREATE TABLE member_memory_consent_event (
    id uuid PRIMARY KEY,
    member_id uuid NOT NULL,
    epoch uuid NOT NULL,
    action text NOT NULL CHECK (action IN ('granted','withdrawn')),
    policy_version text NOT NULL,
    recorded_at bigint NOT NULL
);
CREATE INDEX member_memory_consent_history ON member_memory_consent_event(member_id,recorded_at);
COMMIT;
