# Penny's Workshop — community beta development
Status: Maker-approved MVP direction. First private preview approval slice;
no public route, deployment, payment, or automatic feedback processing.

## Objective
Penny creates useful products, shares explicitly approved beta previews,
collects community feedback, evaluates it under bounded work limits, revises
products and recognizes verified contributions. Maker retains final commercial,
privacy, safety, financial and publication authorization. A private Maker
review interface is required for launch; ordinary feedback should not require
manual SSH commands.

The Maker approved the controlled showroom direction: Penny's growth and
community participation are the durable value, not unrestricted access to
private work. Follow [showroom contract](SHOWROOM.md). Community members
advise, test and improve Penny's products; they do not commission arbitrary
work. Routine quality feedback is community-led. Maker retains the existing
disclosure, security, legal, finance and final-release authority.

## State and ownership
Reuse workshop_task/artifact, business opportunity, quality review, catalog,
community_suggestion and recognition. Migration 035 adds immutable
workshop_preview (source task, exact artifact hash, explicitly reviewed title
and preview text, preview hash, reviewer, expiry and evidence) and withdrawal.
A preview may be approved before all five final quality criteria pass, but
the Maker must review the exact excerpt for safe disclosure and accuracy.
No automatic copy of raw model output. Approval alone does not publish.
One active preview per artifact, at most 20 active and 4096 retained,
maximum seven-day validity (provisional). Revoked quality, integrity drift,
expiry and withdrawal suppress the trusted projection. Historical review
replay does not reactivate. New approval requires fresh evidence.
Only explicit approved projection fields may cross the outbound bridge.

Next schema slice: attach feedback to exact preview ID/version, authenticated
member and existing bounded suggestion record; usefulness 1–5, purchase
interest yes/maybe/no, optional text. Design shared quotas, owner-only
read/correction, retention/erasure and terminal moderation before activation.
No raw feedback in public pages, model authority, or arbitrary task admission.
Aggregate interest is self-reported, not orders or revenue. No reward for
paying or duplicate feedback; attribution requires verified impact and consent.

## Workflow
Private artifact -> exact preview review -> sanitized outbound projection ->
community feedback -> bounded evaluation -> authorized revision -> version
history -> final independent quality review -> Maker commercial release.
A revision is a new artifact, not mutation of the original. Keep failures
and evidence. No automatic spend, sale, direct home listener or public admin
credentials. Reuse existing scheduler and Guardian.

## Acceptance
- [ ] Every public beta preview and final deliverable carries approved Penny
  branding; preview approval binds the rendered brand and content, and commercial
  release independently reviews exact branded bytes. See [brand](PRODUCT_BRAND.md).
- [ ] Maker preview review and withdrawal interface; no SSH for routine review.
- [ ] Approved beta snapshot projection, expiry and cache invalidation on
  withdrawal, no private data or unreviewed artifact.
- [ ] Authenticated feedback intake with shared quotas, deduplication and
  abuse/consent/retention checks; no browsing-triggered inference.
- [ ] Bounded feedback evaluation, reviewed revision requests, version history,
  attribution with consent, corrected/withdrawn feedback handling.
- [ ] Final quality and commercial authorization remain distinct from beta.
- [ ] End-to-end private rehearsal before live publication.

## First feedback implementation
Migration 053 adds local version-bound structured ratings and interest with
owner-only withdrawal and shared suggestion capacity. Separate structured
rows replace the proposed immutable suggestion linkage for rating-only
feedback, so rating content can be removed. Optional textual feedback,
moderation, correction, retention, aggregate projection and reviewed revision
linkage remain pending. See SHOWROOM.md for the exact limits.

## Moderation implementation (054)
Local terminal feedback review and a private aggregate candidate now exist.
Routine feedback moderation still requires a trusted local reviewer; no public
moderation interface or automated scoring is enabled. Eligible, live feedback
is summarized separately from sales and withdrawn/rejected feedback. Public
projection requires its own privacy and cache review; no automatic task creation.
