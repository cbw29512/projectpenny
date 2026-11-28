# Local model business draft intake
Migration 023 introduces explicitly registered internal draft tasks and
immutable quarantined structured candidates. A trusted administrator
submits a bounded brief via the existing scheduler, one live business
draft at a time, at most three admissions per rolling day. These are
provisional beta limits. Existing scheduler pause, business queue cap,
lease and inference timeout apply. Reserved key cannot be submitted by
generic member/internal TaskStore.submit. No member personal memory,
memory-informed task or external network is involved.
Worker generates one private response. Fenced successful completion
atomically stages an exact typed JSON proposal only for a registered
internal draft task. Reject duplicate keys, extra fields, invalid enums,
booleans masquerading as integers, nonzero cash estimates and bounds
violations. An invalid response remains an unsuccessful proposal shape
even if the inference job succeeded. Candidate SHA256 binds exact raw
output; no model-generated evidence is verified. Private trusted
administrator read returns candidate shape and digest for later review.
No automatic opportunity creation, approval, prototype execution, tool
access, publication, spending, market research or earnings. Separate
human evidence review and promotion to the experiment lifecycle still
needed. No live inference run, deployment, real data or external spend;
integration tests use real PostgreSQL and fake model response.
