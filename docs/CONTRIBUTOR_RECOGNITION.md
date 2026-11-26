# Private contributor recognition — first slice
## Objective / state
Migration 011 stores independently reviewed nonpersonal outcomes, explicit
member/outcome/role consent requests, and reviewed attribution records. Evidence
references and fingerprints are stored, not evidence bytes. One request per
owner/outcome/role; one recognition per consent request. Distinguish improved,
unsuccessful and inconclusive results. No payment field or entitlement lookup.

## Logic
Trusted reviewer records an evidenced outcome -> member explicitly requests
private credit using a valid session and exact consent version -> reviewer
independently verifies evidence for that particular contribution -> deterministic
private appreciation record. Replays cannot duplicate outcomes or recognition.
Conflicting outcome evidence is rejected. Multiple contributors receive equal
wording for the same role and outcome. Owner withdrawal deletes live request
and recognition atomically; new consent requires independent review again.
Privacy withdrawal remains possible during identity failure. No inference calls.

## Limits
Initial roles: ideas, testing, bug reports and advice. Private opt-in only; no
public credit, notifications, financial-support attribution, proposal/vote
workflow, verified metric amounts or external evidence storage yet. Outcome
references and evidence must be nonpersonal; a digest is not factual proof.
Trusted administrator must authenticate independently and validate evidence;
member cannot self-verify. Limit 100 concurrent retained requests/member
(provisional). No bulk withdrawal, expiry, correction of verified outcomes or
full deletion from backups/WAL yet. Public attribution must be separate explicit
consent and revocable before public projection. No production deployment.
Apply migrations 001–011 in order.
