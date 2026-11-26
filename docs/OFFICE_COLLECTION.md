# Penny's Office Collection — interactive merchandise showroom

Maker-approved direction; physical commerce deferred. No new spending,
supplier accounts, orders, payments or public deployment authorized.
The secure website-first launch and first digital-product cycle remain first.

## One world, three independent layers

1. Immutable canonical Penny and office artwork; no model-generated markup,
   CSS, text, URLs or alteration of her face, hair, body or room.
2. Reviewed durable virtual inventory and placement events. Achievement
   eligibility is not ownership or purchase authority.
3. Daily presentation: approved shirt color and programmer-humor mug design
   rotate without changing permanent inventory or furnishings. No new task,
   model call, ledger transaction or purchase caused by browsing or rotation.

Use stable versioned design IDs everywhere: scene, inspector, future
merchandise listing, community suggestions and historical media. A design
seen in the office and its physical listing must refer to the same approved
version. A virtual object is not physical property or available stock.

## Daily selection and authority

The server supplies an America/New_York calendar date and reviewed eligible
design IDs. Cycle deterministically through the approved ordered shirt and mug
pools; consecutive dates differ when more than one design is eligible.
Pin one reviewed DailyStyle record and its collection version for each date.
Mid-day pool edits do not rewrite the selected day. Overrides require explicit
review and are date-scoped. On missing/invalid/stale state retain the last
verified presentation or labeled baseline. No browser clock as live authority.
Free baseline variations require Maker approval; earned items require actual
verified eligibility. Daily selection does not acquire or remove possessions.

## Candidate designs

- mug-localhost-v1: There is no place like 127.0.0.1
- mug-sudo-coffee-v1: sudo make coffee
- mug-sleep-404-v1: 404: Sleep Not Found
- mug-cobol-v1: COBOL Never Dies
- mug-works-on-machine-v1: Works on My Machine
- mug-penny-slogan-v1: Financially Underfunded. Sarcastically Overqualified.

Proposed shirt colors: teal, plum, blue, forest, maroon, mustard, charcoal. Future accessories include
mouse pads, stickers, desk mats and milestone collectibles. These are
development concepts, not rights-cleared production designs.

## Inspection and sales

Visitors can inspect the exact design with an accessible enlarged view
and literal phrase text. Long phrases (including localhost) must be
legible in the full-size design, not necessarily on a tiny scene prop.
Community suggestions reuse existing bounded authenticated intake and
review; future voting must share existing limits, not create another
authority or count interest as sales.

Unlisted designs show a clear concept label, no fake buy control, price
or stock. Physical merchandise requires separate print proof, rights and
trademark review, canonical Penny branding, reviewed supplier and listing
terms, price, fulfillment, refunds, taxes, fees and customer-data handling.
Evaluate print-on-demand first; verify actual margins and sandbox checkout
before explicit Maker launch authorization. A withdrawn listing cannot
accept orders even if the virtual design remains visible.

## Proposed state (not installed DDL)

MerchDesign: stable design ID/version, kind, literal phrase/color, local
asset IDs, brand version, artwork digest, rights evidence, review state.
MerchListing: design/version, provider SKU, exact approved print/listing
digests, currency/price, supplier-cost evidence, seller, ledger owner,
approval, state (unlisted/reviewed/active/withdrawn).
DailyStyle: local date, zone, collection version, shirt/mug design IDs,
review/override reference; immutable selected day.
CommunityDesignSuggestion: existing suggestion reference, optional design ID.

Founder merchandise is intended as a separate revenue stream from Penny's
dedicated business earnings. Maker must approve mixed-revenue allocation,
shared costs and brand licensing before sales. Keep correct ledgers, actual
fees/refunds/costs, truthful seller attribution and no invented revenue.

## Acceptance

- [ ] Stable day selection across reloads/devices, midnight/DST, restarts
  and catalog changes; no identity drift or durable-state mutation.
- [ ] Accessible inspection and exact phrase/asset mapping, rights and print
  proof before sale; no arbitrary URL, HTML or text from model output.
- [ ] Unknown/unapproved/revoked IDs blocked. No checkout until authorized.
- [ ] Exact versioned listing, seller, separate accounting, sandbox payment
  and refund/withdrawal tested. No automatic spending.

## Installed development slice

The website includes a read-only, labeled Office Collection preview with
fixed design IDs, readable enlarged mug concepts and a proposed shirt
palette. The deterministic date-selection helper is tested separately;
it accepts an explicit valid calendar date and ordered eligible IDs.
It does not establish trusted ownership, approval, or live day authority.
The current scene and durable inventory are unchanged until the reviewed
DailyStyle snapshot and approved scene assets are integrated. No storefront,
checkout or supplier integration is enabled.
