BEGIN;
CREATE TABLE inference_runtime (
    singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
    enabled boolean NOT NULL DEFAULT false,
    uncertain boolean NOT NULL DEFAULT false,
    last_started bigint,
    last_finished bigint,
    last_result text CHECK(last_result IN ('idle','completed','blocked','interrupted'))
);
INSERT INTO inference_runtime DEFAULT VALUES;
COMMIT;
