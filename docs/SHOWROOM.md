# Penny's controlled showroom — approved MVP direction
Status: requirements approved by Maker, implementation pending.
Penny's growth, personality and community interaction are the durable value.
The community is her advisory and testing team, not her employer. The
showroom is a projection of safe reviewed information, not access to a model
or private Workshop. Do not change the canonical identity or finance contract.

## Visibility state (planned)
| State | Audience | Allowed content |
| --- | --- | --- |
| Secret | Trusted local Maker and authorized private worker | Full private product, evidence, unpublished idea and source assets |
| Showroom | Public visitors | Approved description, selected excerpt or demonstration, safe progress and feedback topics |
| Closed beta | Authorized authenticated testers | Exact approved review edition, scoped to tester and version |
| Released | Public listing and authorized purchasers | Approved listing and exact commercially authorized deliverable |

Visibility applies to an exact immutable edition, not a mutable artifact
or unrestricted URL. Promotion requires existing relevant reviews and
separate authorization. Withdrawal, expiry, quality revocation, brand drift
or integrity mismatch suppress future access. Previously downloaded material
cannot reliably be recalled. Watermarks, access controls and delayed
disclosure deter copying but cannot guarantee secrecy after disclosure.
Do not imply ownership of ideas or copyright solely because of a timestamp.

## Proposed schema (not installed)
- ShowroomEdition: stable product/edition/version ID; source artifact digest;
  approved brand/version and preview digest; explicit visibility; review
  reference; disclosure expiry; withdrawal marker. Public projection carries
  only allowlisted fields, never private source identifiers that expose paths,
  internal prompt content, keys, private evidence or full research.
- BetaGrant: authenticated tester ID, exact edition ID/digest, reviewed scope,
  grant/expiry/revocation state. No public object URL for private assets.
  Any tester-specific watermark uses an opaque identifier, not personal
  information exposed to other testers. Exact rendered variant must meet
  the brand/disclosure contract. No live payment or third-party DRM.
- Feedback: existing suggestion and preview IDs, member, bounded category,
  usefulness and purchase-interest choices, optional comment, moderation
  and correction/withdrawal state. No free-form instruction authority.
- Decision/Revision: link reviewed feedback and prior edition to authorized
  work and new immutable artifact; factual explanation and consented credit.
  No edit of historical reviews or product bytes.

## Workflow
1. Penny privately evaluates an idea and creates a useful prototype.
2. Review exact safe, branded excerpts for showroom. Delay disclosure if
   commercially sensitive; never automatically dump raw model output.
3. Community votes on features, reports problems, gives usability/pricing
   feedback and proposes improvements. Aggregate interest is not revenue.
4. Only the approved bounded scheduler may evaluate suggestions and request
   revisions. No visitor-selected tools, files, prompts, private research
   queries, custom deliverable generation or automatic product publishing.
5. Approved testers can evaluate a controlled review edition; access expires,
   can be revoked and is isolated per edition and member. Treat any disclosed
   content as potentially copied. No guarantee of copy prevention.
6. Penny explains actual decisions and improvements in her own voice, thanks
   verified contributors with consent, and publishes only safe reviewed
   progress. Preserve setbacks and do not invent feedback or results.
7. Separate final content, legal, security, brand, price, seller, payment and
   commercial-release reviews. Community approval is advice, not authority.

## Acceptance
- [ ] Secret drafts and full source assets never appear in public payloads,
  bundles, caches, client state, logs or object listings.
- [ ] Exact branded showroom excerpt and beta grants are separate from
  commercial authorization; expiry and revocation tested across caches.
- [ ] Cross-member, cross-edition, replay, scraping and arbitrary-generation
  abuse tests; bounded shared quotas with no inference on passive browsing.
- [ ] Feedback intake and aggregation preserve privacy, consent, correction,
  deletion and evidence; no invented demand, revenue, voters or endorsements.
- [ ] Decisions/revisions link actual reviewed contributions; credit is
  optional and consented. Show aggregate progress and real outcomes.
- [ ] Community handles routine feedback, Maker handles sensitive disclosure
  and exceptional decisions through trusted local review. No cloud admin.
- [ ] First branded checklist demonstrates private -> showroom -> controlled
  beta -> revised edition -> final review in a private rehearsal.

No new spending, live beta, publication, payments or deployment authorized.
Exact tester eligibility, rate limits, retention and commercial pricing
remain pending review; do not infer them from this direction.

## First implemented slice (migration 053)
Local authenticated structured feedback binds an exact live reviewed preview
ID and SHA-256. One rating per member/version, usefulness 1–5 and interest
 yes/maybe/no; no free text, no inference or automatic revision. It shares
existing suggestion quotas under the scheduler lock, rather than duplicating
immutable suggestion bodies. Owner-only read and withdrawal; withdrawal
clears rating/interest, retains a minimal member/request/version tombstone
for duplicate prevention and quota accounting (not full deletion). No
public endpoint, aggregation, moderator workflow, correction/resubmission,
retention/purge, branded release or beta grants yet. Existing caps reused
provisionally; active unmoderated feedback consumes pending capacity, so
this local rehearsal must not be enabled publicly until moderation exists.
No authorization for actual publication or deployment. CI pending.

## Moderation and private aggregate (migration 054)
Trusted local reviewer can record a terminal eligible/rejected decision with
fixed reasons, bound to exact displayed rating, interest and preview digest.
No copies of the rating or interest are placed in the immutable decision.
Owner status exposes only pending/eligible/rejected/withdrawn, not reviewer
identity. Terminal review frees shared pending capacity, not the rolling
submission or retained-record budget. Withdrawal still clears the values and
excludes the row from aggregates even after eligibility. New eligibility
requires a live integrity-checked preview; rejection can close stale work.
Private aggregate recomputes under the shared lock from current eligible
nonwithdrawn feedback; suppress samples below five (provisional) and expose
only counts and rating sum for larger samples. This is not anonymous or safe
for repeated public publication: small cells and differencing remain risks.
No public endpoint, automatic moderation, correction, retention/purge or
revision scheduling. No claimed purchases, revenue or actual community votes.

## Local moderation worklist
A bounded trusted-local worklist lists oldest pending feedback (maximum 20),
exact review values and current preview availability. No owner identity,
request key, source asset or private product text is returned. Stale feedback
remains visible to the reviewer for rejection, and reviewed/withdrawn rows
leave the queue. No public or model-facing API, automatic moderation or
scheduling. The shared integration fixture is reused without duplicating
its setup or inherited test methods. CI verification remains required.

## Reviewed revision admission (057)
CI 46059575858 passed the integrated private business rehearsal. Revision
admission now binds a private digest of the live eligible aggregate (minimum
five), parent artifact digest and exact preview to a trusted Maker-reviewed
improvement brief and evidence fingerprint. Recheck the digest under the
scheduler lock before admitting a new immutable Workshop task. One revision
per preview, exact replay only; use existing experiment, pause, daily and
per-opportunity caps. New prototype is unreviewed; no inherited quality,
brand, publication, payment or commercial authority. Prior artifact remains
unchanged. The worker receives the prior checklist and reviewed brief, not
individual ratings, member IDs or raw visitor messages. Long prompts exceeding
2000 chars are refused rather than truncated. The aggregate is evidence of
self-reported opinions, not demand or specific requested features.
A later feedback withdrawal suppresses current aggregates but does not
retroactively undo a previously authorized private task; historical digest
contains no individual values. Future completion-time source revocation,
reviewed revision comparison, closed beta, written suggestions, consented
credit, retention and public progress projection remain separate work.
Synthetic regression tests added; CI pending. No live release.
