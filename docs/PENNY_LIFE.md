# Penny's life, office and sleep — planned extension

Status: Maker-approved concept, not implemented. Core kiosk and business
launch work remains first. No new expenditure, public deployment or
automatic authority granted by this document.

## Objective

The office visibly represents Penny's actual growth; a daily off-duty cycle
provides an honest maintenance window; optional dreams offer fictional
entertainment. Preserve the same character and evidence rules.

## Proposed data and state contracts

Names below describe intended fields, not installed tables.

OfficeItem: stable item key, approved asset key, kind (virtual_reward,
real_equipment_representation), entitlement milestone, fulfillment reference,
reviewed timestamp, active/revoked state. Reuse existing milestone and
purchase evidence instead of inventing parallel financial records.
Wishlist: item key, purpose, estimated cost with date/source, priority,
eligibility, approval/fulfillment status. Actual affordability requires
reviewed available funds and authorized purchase; unknown means unknown.
Free digital rewards require no fabricated cost or receipt.

RestPolicy: Maker-approved version, enabled, IANA zone, local bedtime,
local wake time. Proposed default America/New_York, 00:00–08:00 wall-clock.
Ordinarily eight hours; DST nights may be seven or nine elapsed hours.
RestState: awake, draining, asleep, blocked, unavailable; authoritative
server timestamp, next transition, policy version, verified work gate.
Rest never overrides manual pause, uncertainty, leases or Guardian.
DreamScene: approved local asset/story key, bounded duration, explicit
fiction flag. No business identifiers, visitors or financial fields.
Dream selection lives in presentation state only.

## Operational flow

1. At bedtime, stop new generation claims and new business planning using
   the existing scheduler. Let fenced work finish or enter verified recovery.
2. Report draining while active work remains; report asleep only when the
   admission/claim gate is effective and no task is running. Uncertain
   inference remains blocked, not cosmetically asleep.
3. Keep database, website, backups and essential monitoring available.
   Allow bounded asynchronous intake only if existing quotas, privacy and
   deadlines can be honored. Otherwise display unavailable until wake.
4. Provide a server-derived wake countdown, not a browser-clock guess.
5. At wake, remove the scheduled rest restriction only. Do not clear
   manual pause, expired tasks, security stops or uncertainty.
6. Show an evidence-based morning report: outcomes, failures, next
   authorized objective and reconciled financial impact if available.

## Dream presentation

Optional viewer-controlled, clearly labeled "Fictional dream — entertainment,
not actual business activity." Use randomly chosen approved local scenes,
such as negotiating with a toaster or a castle of graphics cards. No
realistic fake transaction, supporter or financial records. Dreams are not
conscious experiences, internal reasoning or business proposals.
Start with local assets and zero inference cost; no visitor-triggered model
calls or paid media generation. Stop on wake, stale data, hidden page or
viewer opt-out; respect reduced motion. Never let dream content overwrite
verified activity, speech, diary, tasks, memory, ledger or permissions.
Dreams are the only explicitly fictional entertainment exception to the
truthful activity display, isolated from real status.

## Office progression

Begin with approved modest room assets. Earn free decorations and trophy
displays from verified achievements; depict real hardware only after
evidence-backed fulfillment and Maker approval. Retain corrections and
revocations, distinguish aspirational wishlist previews from owned items,
and never claim a virtual room is actual property. Milestone unlock is not
spending authority; purchases use existing Vault approval and reconciliation.

## Persistent visual continuity — required at initial launch

Do not regenerate the character or office on requests, reloads, model changes,
new sessions or social exports. Compose fixed versioned approved local assets
with a durable world snapshot. The initial launch may use a single static
baseline; later inventory and wardrobe progression must extend that baseline.

Proposed schema (not installed):
- CharacterManifest: version, immutable asset digests, canonical face, hair,
  proportions, palette, art style, approved expression/pose variants.
- OfficeBaseline: version, room geometry, fixed viewpoint, approved background
  asset digest, initial stable item IDs and placements.
- WorldEvent: sequence, event ID, prior revision, action (add, remove, move,
  equip, unequip, replace, correct), item/asset ID, slot/placement, approval
  and evidence references, timestamp. Append-only; idempotent, ordered and
  conflict-checked. Baseline and events reconstruct the same world after restore.
- WorldSnapshot: revision, manifest/baseline versions, active item placements,
  equipped outfit, generated timestamp and integrity digest. Public projection
  excludes private evidence and operational identifiers.

Penny can propose changes; only an authorized evidence-backed event changes
persistent appearance or inventory. A free virtual rearrangement needs no
purchase; real purchases retain Vault approval and reconciliation. Removal,
replacement and correction must preserve history. An earned item is not
automatically equipped or placed. No unapproved makeover or scene reset.
Expression, pose, lighting and camera crops are presentation-only and must
not change canonical features or item placement. Dream scenes remain separate.

Use the same canonical character asset family for the kiosk, website, products,
and eventual streams/social content. Historical media retains its original
world revision. Never silently substitute a newly generated character or room.
On invalid/stale state, show last verified snapshot with honest status, or
the explicitly labeled baseline if none exists. Fail closed on unknown assets.

Acceptance: identical world revision yields identical asset IDs, outfit and
placements across sessions, clients, model upgrades and restart/restore;
approved add/remove/move/equip affects only intended slots; replay cannot
duplicate objects; invalid or unapproved transitions cannot alter the world;
offline state and dream mode cannot rewrite persistent state.

## Installed website baseline (provisional artwork)

The public development preview now composes three fixed same-viewBox SVGs
(room, Penny, foreground desk) in HTML/CSS with no model-controlled URL,
HTML, coordinate or style input. The original drawing is preserved exactly
in the same painter order. SHA-256 pins and scene markup regression tests
guard accidental changes; the pins themselves require trusted review and
are not a substitute for protected branches or deployment access control.
This is not final Maker-approved artwork or a persistent inventory engine.
The worker has no website mutation capability in Guardian; actual production
filesystem permissions, credentials and branch protection require verification.
Future state rendering must use allowlisted IDs/slots and keep this baseline
independent of model output. No production deployment is authorized.

## Acceptance before activation

- [ ] Office display matches verified fulfillment and correction state;
  wishlist and unfulfilled milestones cannot appear owned.
- [ ] Rest gate enforced atomically at task claim and planning; active task
  drains without losing a fence; manual pause and uncertainty survive wake.
- [ ] Midnight, DST transitions, restart during rest, deadline expiry,
  concurrent claims, configuration changes and offline fallback tested.
- [ ] No business/chat inference while asleep; message admission remains
  bounded; backups work without reopening generation.
- [ ] Dreams optional, labeled, visually separate, no model requests,
  private data, external network or persistent business writes.
- [ ] Morning and bedtime reports only from verified records.
- [ ] Maker approves actual schedule and assets before activation.
