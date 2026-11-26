# Private checklist quality review and export
Migration 026 stores append-only, digest-bound human reviews. Five fixed
criteria: usefulness, accuracy, originality, privacy, completeness. All
must pass for private export. Reviewer attests independent evidence;
a hash alone does not prove quality or truth. Exact source-ref replay
returns the existing review, never reactivates it. Latest review controls
export, and terminal revocation requires a new artifact version. Revocation
can be recorded even when artifact integrity fails. Failed reviews remain
in history. No automatic business measurement or revenue inferred.
Export takes exact latest passed review ID and artifact hash, rechecks
the fenced successful source and deterministic rendering under the shared
transaction lock, and returns UTF-8 bytes plus generated safe filename and
text/plain media type. No file path from model, filesystem write, public
route, store listing, payment, or sale. Authenticated operator interface
and actual downloadable UI remain pending. Revocation cannot retract
bytes already exported. Existing Guardian admin review capability reused;
no new public or model permissions. Review rubric is provisional, not
legal or professional certification. Synthetic tests only. No deployment.
