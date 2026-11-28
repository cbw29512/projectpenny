BEGIN;
-- Private operator-owned identity binding; never auto-create from cloud data.
CREATE TABLE bridge_member (
    cloud_owner uuid PRIMARY KEY,
    local_member uuid UNIQUE NOT NULL,
    enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE bridge_receipt (
    question_id uuid PRIMARY KEY,
    cloud_owner uuid NOT NULL REFERENCES bridge_member(cloud_owner),
    local_member uuid NOT NULL,
    fence uuid UNIQUE NOT NULL,
    task_id uuid UNIQUE NOT NULL REFERENCES work_task(id),
    payload_sha256 text NOT NULL CHECK(payload_sha256 ~ '^[0-9a-f]{64}$'),
    expires_at bigint NOT NULL,
    admitted_at bigint NOT NULL CHECK(expires_at>admitted_at),
    acked_at bigint CHECK(acked_at IS NULL OR (acked_at>=admitted_at AND acked_at<expires_at))
);
CREATE INDEX bridge_pending_ack ON bridge_receipt(expires_at) WHERE acked_at IS NULL;
COMMIT;
