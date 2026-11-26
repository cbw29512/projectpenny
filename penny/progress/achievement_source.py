"""Derive eligibility from current, explicitly reviewed source evidence."""
from .achievement_state import Achievement
from .state import digest
from .timeline_state import source_digest
from .derive import derive
from .timeline import _source
from penny.vault.budget import _matched


def source_locked(conn,now,code):
    """Return private binding and expiry, or None. Caller holds scheduler lock."""
    if code in (Achievement.FIRST_DOLLAR,Achievement.IN_THE_GREEN):
        row=conn.execute("""SELECT version,payload,payload_sha256,generated_at,expires_at
            FROM progress_snapshot ORDER BY version DESC LIMIT 1""").fetchone()
        if not row or not row["generated_at"]<=now<row["expires_at"]:
            return None
        payload=row["payload"]
        if digest(payload)!=row["payload_sha256"] or payload["finance"] is None:
            return None
        finance=derive(conn,now,finance=True,business=False)["finance"]
        if finance is None or finance!=payload["finance"]:
            return None
        match=_matched(conn,now)
        if match is None:
            return None
        net=finance["commercial_receipts"]-finance["commercial_refunds"]
        eligible=(net>=100 if code is Achievement.FIRST_DOLLAR else
                  net>0 and finance["commercial_result_after_recorded_costs"]>0)
        if not eligible:
            return None
        # Bind reconciliation identity as well as aggregate values. A new
        # reconciliation needs a fresh explicit review, even if totals match.
        binding={"code":code.value,"version":row["version"],
                 "snapshot":row["payload_sha256"],"reconciliation":str(match["id"])}
        return source_digest(binding),row["expires_at"]
    if code is Achievement.PROOF_OF_CONCEPT:
        row=conn.execute("""SELECT e.id,e.experiment_event_id,e.source_sha256,e.occurred_at
            FROM progress_timeline_event e
            LEFT JOIN progress_timeline_suppression s ON s.event_id=e.id
            WHERE e.kind='target_met' AND s.event_id IS NULL
            ORDER BY e.occurred_at,e.sequence LIMIT 1""").fetchone()
        if row is None:
            return None
        source=_source(conn,row["experiment_event_id"],now)
        if source is None or source!=("target_met",row["occurred_at"],row["source_sha256"]):
            return None
        return source_digest({"code":code.value,"event":str(row["id"]),
                              "source":row["source_sha256"]}),now+3600
    raise ValueError("unsupported achievement")
