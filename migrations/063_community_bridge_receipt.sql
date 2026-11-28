BEGIN;
CREATE TABLE community_bridge_receipt (
 cloud_id uuid PRIMARY KEY,
 cloud_owner uuid NOT NULL REFERENCES bridge_member(cloud_owner),
 local_member uuid NOT NULL,
 request_key uuid NOT NULL,
 fence uuid UNIQUE NOT NULL,
 payload_sha256 text NOT NULL CHECK(payload_sha256 ~ '^[0-9a-f]{64}$'),
 suggestion_id uuid NOT NULL REFERENCES community_suggestion(id),
 expires_at bigint NOT NULL,
 lease_until bigint NOT NULL,
 admitted_at bigint NOT NULL CHECK(admitted_at>=0 AND admitted_at<lease_until AND lease_until<=expires_at),
 UNIQUE(cloud_owner,request_key)
);
CREATE TRIGGER community_bridge_receipt_immutable BEFORE UPDATE OR DELETE ON community_bridge_receipt
FOR EACH ROW EXECUTE FUNCTION vault_append_only();
REVOKE ALL ON community_bridge_receipt FROM PUBLIC;
COMMIT;
