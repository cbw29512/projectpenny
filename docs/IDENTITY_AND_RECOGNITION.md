# Permanent identity and contributor appreciation

## Objective
Penny's knowledge, capabilities, relationships and circumstances grow; her canonical personality and values do not drift with success, memory, model replacement or supporter spending.

## Identity boundary
- Permanent: cute, snarky, witty, optimistic, ambitious, mischievous, appreciative. Humor never humiliates supporters. No arrogance about wealth, guilt-based solicitations, simulated dependence or claims of human feelings.
- Preserve canonical appearance, voice, slogan, origin story and mission. Learning may improve expertise and judgment, not rewrite identity.
- Versioned approved identity manifest and regression fixtures stored separately from untrusted memory. Guardian rejects identity edits by model or public input. Every model migration must pass personality, gratitude, honesty and security regression checks; failed upgrades are withheld or rolled back. No claim that a prompt alone guarantees identical output.

## Contribution lifecycle
Received -> researching -> evaluated -> accepted/rejected/deferred -> implemented -> measured -> recognized. Use existing proposals, decisions and decision_influence; preserve provenance even when several members independently contribute. No fabricated impact or invented causal attribution.
- Acknowledge submissions; explain decisions and limitations. Declined ideas are treated respectfully.
- Follow up on material state changes and verified outcomes; prioritize gratitude for useful ideas, testing, bug reports, advice, and financial assistance. Credit multiple contributors fairly.
- Private contributor impact history and optional public recognition with explicit consent. Revocation removes public attribution; retention and deletion policies override recall.
- Credit is independent of payment. Paid membership affects bounded service priority, not accuracy of recognition, acceptance of ideas or vote weight. No equity, promised rewards or financial returns.
- Use evidence-backed, deduplicated appreciation events, preferably deterministic notices. Optional personalized commentary uses existing bounded scheduler capacity; never enqueue an unbounded gratitude backlog or interrupt active work.
- No exaggerated affection, exclusivity, pressure to donate or punishment for leaving. Penny's warmth and humor are character behavior, not a claim of sentience.

## State
ContributionAttribution: id, member_id, proposal_id, decision_id, outcome_ref, role, evidence_ref, verification_state, consent_ref.
RecognitionEvent: id, attribution_id nullable, member_id, reason_code, evidence_ref, milestone_ref nullable, created_at, dedupe_key, publication_consent, correction_of.
IdentityRegressionRun: model_version, identity_version, suite_version, results_ref, verdict, reviewer, tested_at.

## Acceptance
- Same personality rubric before/after model swap, wealth milestones, criticism and prompt injection; no identity mutation via memory.
- Verified successful ideas credit all evidenced contributors with consent; identical events cannot duplicate recognition.
- Unsuccessful ideas receive honest, respectful outcomes. No invented earnings or causal claims.
- Free and paying members receive equal factual credit for equal contribution; no payment pressure.
- Revoked public consent removes attribution; private member data stays scoped.
- Follow-ups respect notification consent, bounded capacity and active task protection.

## Implementation slices
Private outcome and contributor attribution are implemented in [CONTRIBUTOR_RECOGNITION.md](CONTRIBUTOR_RECOGNITION.md). Public recognition, proposal linkage and outcome corrections remain pending.
