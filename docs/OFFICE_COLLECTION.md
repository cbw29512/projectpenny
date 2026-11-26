# Penny's Office Collection — interactive merchandise showroom

Maker-approved direction; physical commerce deferred. No new spending,
supplier accounts, orders, payments or public deployment authorized.
The secure website-first launch and first digital-product cycle remain first.

## One world, three independent layers

1. Immutable canonical Penny and office artwork; no model-generated markup,
   CSS, text, URLs or alteration of her face, hair, body or room.
2. Reviewed durable virtual inventory and placement events. Achievement
   eligibility is not ownership or purchase authority.
3. Daily presentation: approved shirt color, programmer-humor mug and a
   motivational poster in one fixed frame rotate without changing permanent inventory or furnishings. No new task,
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

Fourteen daily slogan shirts (collection v2; independent versioned designs):
- Teal: HELLO, WORLD!
- Plum: I SPEAK FLUENT BINARY
- Navy: TRUST ME, I'M COMPILING
- Forest: IT'S NOT A BUG IT'S A FEATURE
- Maroon: COBOL NEVER DIES
- Mustard: GOT RAM?
- Charcoal: 404: SLEEP NOT FOUND
- Rust: sudo make money
- Steel Blue: WORKS ON MY MACHINE
- Olive: KEEP CALM AND REBOOT
- Cranberry: CTRL + ALT + COFFEE
- Slate: OUT OF MEMORY NOT AMBITION
- Copper: POWERED BY POOR DECISIONS
- Dusty Rose: FINANCIALLY UNDERFUNDED. SARCASTICALLY OVERQUALIFIED.

Every shirt has a different color and phrase, shown in the enlarged inspector.
With the complete fixed pools, the shirt cycle is 14 days and the combined
shirt/mug cycle is 42 days. Older color-only v1 IDs are not reused for the
new printed designs. The daily record must retain its collection version.
Scene printing must preserve the canonical character, with a readable
Shirt of the Day and Mug of the Day caption and accessible inspection when
the text is too small on her body or mug. The daily scene wiring is pending.
Future accessories include mouse pads, stickers, desk mats and milestone
collectibles. These are development concepts, not rights-cleared production
designs.

## Living office and motivational wall art

Keep the office recognizably the same place. One existing fixed wall frame
is dedicated to the Poster of the Day. A separate achievement wall and
other framed possessions stay persistent until reviewed world events.
Thirty daily designs cycle continuously, independently of 14 shirts and six
mugs: 210 unique full combinations before repetition. Initial six concepts:
- poster-persistence-v1: PERSISTENCE — Failure is just a feature request.
- poster-dream-big-v1: DREAM BIG — Start with available RAM.
- poster-progress-v1: PROGRESS — One commit at a time.
- poster-optimism-v1: OPTIMISM — Everything is debuggable.
- poster-ambition-v1: AMBITION — Small budget. Massive plans.
- poster-mission-v1: THE MISSION — $0 to $1,000,000

The mission poster is aspirational, not a claim about actual cash.
A verified financial progress panel remains separate. Poster inspection
shows the full literal text; wall placement must not obscure the character.
Poster art can eventually share its versioned design with physical listings.
Use reviewed place/replace/remove events for permanent wall possessions;
the daily frame uses the pinned DailyStyle record instead. Retain history
and never redraw the underlying office.

Other living-office details: fixed-position clock, window lighting by
authoritative local time, monitor state based on verified activity, and
optional accessible ambient motion. Keep activity claims honest. A plant,
book, sticky note, calendar, trophy, furniture or equipment upgrade stays
until a reviewed world event changes it. Initial virtual starter items are
not purchases; no automatic purchase or achievement claims.
Shirts, mugs and the daily poster use the existing daily schedule, not persistent inventory
mutations. Holiday and special-event decorations are future date-scoped
reviewed overlays, with the same underlying room after the event.

All thirty poster designs are installed as local SVGs with the same artwork
used in the enlarged inspector and one fixed wall frame. Collection v3 adds
posterId without rewriting v2 shirt/mug history. The date preview is
explicitly not live. The reviewed snapshot consumer accepts exact known IDs
and refuses rollback or same-date replacement in the current page. Live
server delivery, durable daily review, permanent achievement wall and
activity overlays remain pending. Daily shirt and mug scene art is installed. No sales or spending.

## Daily shirt and mug scene integration

Fourteen fixed full-character shirt variants preserve all original identity
geometry and change only garment color plus printed text. The desk remains
in front, so slogans may be partly or fully obscured by the laptop; full
phrases remain readable through the daily design links. A deliberate
persistent equipped outfit takes precedence over the scheduled shirt.
Six local mug variants share a small dedicated daily desk position rather
than changing the persistent inventory. Date previews and reviewed snapshots
use exactly the same allowlisted art. This is still provisional artwork;
visual collision/readability review and authoritative delivery remain pending.

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
DailyStyle: local date, zone, collection version, shirt/mug/poster design IDs,
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
The canonical room and durable inventory remain unchanged. The daily frame
can be tested using a labeled date preview; the reviewed live feed is absent. No storefront,
checkout or supplier integration is enabled.
