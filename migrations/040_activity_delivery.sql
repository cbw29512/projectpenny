BEGIN;
-- Local opt-in; no automatic entitlement to spend hosting credits.
CREATE TABLE activity_delivery_control (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 enabled boolean NOT NULL DEFAULT false,
 config_sha256 text CHECK(config_sha256 ~ '^[a-f0-9]{64}$'),
 daily_limit integer NOT NULL DEFAULT 0 CHECK(daily_limit BETWEEN 0 AND 1440),
 day_bucket bigint NOT NULL DEFAULT 0 CHECK(day_bucket>=0),
 attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 1440),
 not_before bigint NOT NULL DEFAULT 0 CHECK(not_before>=0),
 last_result text NOT NULL DEFAULT 'never' CHECK(last_result IN
 ('never','interrupted','published','refused','unavailable','backoff','unauthorized','uncertain')),
 CHECK(NOT enabled OR (config_sha256 IS NOT NULL AND daily_limit>0))
);
INSERT INTO activity_delivery_control DEFAULT VALUES;
CREATE TABLE activity_delivery_review (
 id uuid PRIMARY KEY,
 enabled boolean NOT NULL,
 daily_limit integer NOT NULL CHECK(daily_limit BETWEEN 0 AND 1440),
 config_sha256 text CHECK(config_sha256 ~ '^[a-f0-9]{64}$'),
 reviewed_at bigint NOT NULL,
 operator_uid bigint NOT NULL CHECK(operator_uid>=0)
);
CREATE TRIGGER activity_delivery_review_immutable BEFORE UPDATE OR DELETE ON activity_delivery_review
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON activity_delivery_control,activity_delivery_review FROM PUBLIC;
COMMIT;
