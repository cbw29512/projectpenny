"""Bounded exact suggestion references for reviewed Workshop admissions."""
import re
from penny.memory.review import _valid_id
from penny.community.suggestion_state import digest


def validate_sources(suggestions):
    # Immutable tuple of (UUID, exact reviewed body digest); never raw text.
    if type(suggestions) is not tuple or len(suggestions)>3:
        raise ValueError("at most three reviewed suggestions")
    for source in suggestions:
        if (type(source) is not tuple or len(source)!=2 or not _valid_id(source[0])
                or type(source[1]) is not str or not re.fullmatch(r"[a-f0-9]{64}",source[1])):
            raise ValueError("invalid suggestion reference")
    if len({s[0] for s in suggestions})!=len(suggestions):
        raise ValueError("duplicate suggestion reference")
    return tuple(sorted(suggestions,key=lambda s:s[0]))


def stored_sources(conn,task_id):
    rows=conn.execute("""SELECT suggestion_id,body_sha256 FROM workshop_revision_suggestion
        WHERE task_id=%s ORDER BY suggestion_id""",(task_id,)).fetchall()
    return tuple((r["suggestion_id"],r["body_sha256"]) for r in rows)


def eligible_sources(conn,sources,now):
    for source,expected in sources:
        row=conn.execute("""SELECT s.body,s.body_sha256,r.body_sha256 AS reviewed_sha256,
            r.verdict,r.reviewed_at FROM community_suggestion s
            JOIN community_suggestion_review r ON r.suggestion_id=s.id WHERE s.id=%s""",
            (source,)).fetchone()
        if (not row or row["verdict"]!="eligible" or row["reviewed_at"]>now
                or row["body_sha256"]!=expected or row["reviewed_sha256"]!=expected
                or digest(row["body"])!=expected):
            return False
    return True
