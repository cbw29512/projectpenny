"""Transactional helpers; caller holds the shared scheduler lock."""
from .maintenance_state import MaintenanceAction


def apply_changes(conn, task_id, proposal, rows, reviewer, ref, mark, now, retention, version):
    # Preserve original text. Replacement has its own provenance through the
    # successful maintenance task and its quarantined proposal/source links.
    replacement_id = None
    if proposal.action in (MaintenanceAction.CORRECT, MaintenanceAction.CONSOLIDATE):
        # Do not silently merge different kinds or extend source retention.
        kinds = {row["kind"] for row in rows}
        if len(kinds) != 1:
            raise ValueError("mixed memory kinds require separate review")
        expires = min(now+retention, *(row["expires_at"] for row in rows))
        conn.execute(
            "INSERT INTO memory_candidate (source_task_id,kind,content) VALUES (%s,%s,%s)",
            (task_id,rows[0]["kind"],proposal.replacement),
        )
        conn.execute(
            """INSERT INTO business_memory
               (source_task_id,kind,content,evidence_sha256,evidence_size,review_ref,
                reviewed_by,approved_at,expires_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (task_id,rows[0]["kind"],proposal.replacement,mark.digest,mark.byte_count,
             ref,reviewer,now,expires),
        )
        conn.execute("INSERT INTO business_memory_event VALUES (%s,'approved',%s,%s,%s,%s)",
                     (task_id,reviewer,ref,now,version))
        replacement_id = task_id
    for row in rows:
        source = row["source_task_id"]
        conn.execute("UPDATE business_memory SET revoked_at=GREATEST(%s,approved_at) WHERE source_task_id=%s",
                     (now,source))
        conn.execute("INSERT INTO business_memory_event VALUES (%s,'revoked',%s,%s,%s,%s)",
                     (source,reviewer,ref,now,version))
    return replacement_id
