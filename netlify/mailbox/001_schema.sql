BEGIN;
-- Separate cloud database. Never apply to the NucBox private database.
CREATE TABLE mailbox_control (
    singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
    enabled boolean NOT NULL DEFAULT false
);
INSERT INTO mailbox_control DEFAULT VALUES;
-- Private beta allowlist. Only a trusted identity administrator provisions it.
CREATE TABLE mailbox_member (
    id uuid PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true
);
CREATE TABLE mailbox_question (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES mailbox_member(id),
    request_key uuid NOT NULL,
    body text NOT NULL CHECK(length(body) BETWEEN 1 AND 2000 AND octet_length(body)<=8000),
    submitted_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK(expires_at>submitted_at),
    state text NOT NULL CHECK(state IN ('submitted','claimed','locally_accepted','answered','rejected','expired')),
    fence uuid UNIQUE,
    lease_until timestamptz,
    local_task_id uuid UNIQUE,
    answer text CHECK(length(answer) BETWEEN 1 AND 16000 AND octet_length(answer)<=64000),
    UNIQUE(owner_id,request_key),
    CHECK(state NOT IN ('claimed','locally_accepted','answered') OR (fence IS NOT NULL AND lease_until IS NOT NULL)),
    CHECK(state NOT IN ('locally_accepted','answered') OR local_task_id IS NOT NULL),
    CHECK((state='answered')=(answer IS NOT NULL))
);
CREATE UNIQUE INDEX mailbox_one_outstanding ON mailbox_question(owner_id)
WHERE state IN ('submitted','claimed','locally_accepted');
CREATE INDEX mailbox_recent ON mailbox_question(submitted_at);
CREATE INDEX mailbox_owner_recent ON mailbox_question(owner_id,submitted_at);
COMMIT;
