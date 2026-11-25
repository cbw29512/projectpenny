# Memory-informed private reasoning

## Objective and state
A trusted internal adapter may submit an explicitly memory-informed business draft
via submit_informed. The stored internal member=NULL and reserved key prefix
determine the claim's memory_enabled flag; neither public text nor a member's
chosen key grants access. Ordinary jobs and learning-review intake remain isolated.
The recall adapter independently checks database ownership, fence, lease and pause.
The request envelope has task text and at most three reviewed memory records with
source UUID, kind and content (1500 aggregate content chars). No schema change.

## Flow
Claim -> check remaining budget -> optional fenced recall -> recalculate budget ->
validate bounded envelope in parent -> one loopback inference in child -> validate
envelope again -> canonical system prompt unchanged; JSON task/memories only in
user role -> Guardian draft check -> fenced private outcome.
Empty recall falls back to ordinary draft. Recall failure blocks, without retry.
A 4500-character rendered context and 48000-byte wire cap are provisional; malformed
or oversized context fails closed. Character limits are not tokenizer guarantees;
live GPU context and prompt truncation testing remain necessary.

## Limitations
Only newest eligible memories are retrieved, not relevance-ranked. Model behavior
may still be influenced by injection or incorrect evidence; framing is not a
security boundary. No tools, external action or public delivery. No automated
review admission, approval, correction, consolidation or personal member memory.
In-flight snapshots cannot be retroactively recalled on revocation. Production
authentication and database privileges, source-level recall audit and behavioral
certification are pending. No identity changes or new paid services.
