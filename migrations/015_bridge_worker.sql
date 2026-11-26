BEGIN;
-- Operator enables explicitly after local and provider checks.
CREATE TABLE bridge_control (
    singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
    enabled boolean NOT NULL DEFAULT false,
    not_before bigint NOT NULL DEFAULT 0 CHECK(not_before>=0),
    blocked_reason text CHECK(blocked_reason IN ('authentication','remote_conflict','local_integrity'))
);
INSERT INTO bridge_control DEFAULT VALUES;
ALTER TABLE bridge_receipt ADD COLUMN remote_rejected_at bigint
    CHECK(remote_rejected_at IS NULL OR (remote_rejected_at>=admitted_at AND remote_rejected_at<expires_at));
COMMIT;
