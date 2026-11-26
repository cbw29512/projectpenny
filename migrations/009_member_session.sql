BEGIN;
-- Store only a digest of a cryptographically random bearer credential.
CREATE TABLE member_session (
    id uuid PRIMARY KEY,
    member_id uuid NOT NULL,
    token_sha256 text NOT NULL UNIQUE CHECK (token_sha256 ~ '^[a-f0-9]{64}$'),
    issued_at bigint NOT NULL,
    expires_at bigint NOT NULL CHECK (expires_at > issued_at),
    revoked_at bigint CHECK (revoked_at >= issued_at)
);
CREATE INDEX member_session_owner ON member_session(member_id,expires_at)
    WHERE revoked_at IS NULL;
COMMIT;
