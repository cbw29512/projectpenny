# MVP / Definition of Done — website-first launch
Approved direction: Penny's Forgotten Website is the initial product. Social
broadcasts and platform adapters are deferred until the website is proven.
Retain the existing tested core, canonical constitution and security contracts.
Maker-directed operating references: [SOUL](../SOUL.md), [GOALS](../GOALS.md),
[PENNY](../PENNY.md). They document the pinned identity and approved work
priorities; runtime authority remains in Guardian and durable state.
No additional spend, deployment, live payments or NucBox changes authorized.

## Launch sequence
- [ ] Forgotten office scene: Penny is an ambitious AI whose modest hardware
  limits her capabilities; the Maker's abandonment/redemption story is disclosed fiction.
- [ ] Initial visual continuity gate: fixed approved canonical character and
  office baseline across visits, sessions, devices and model changes. No random
  regeneration; later persistent changes use authorized world events. See
  [visual continuity contract](PENNY_LIFE.md#persistent-visual-continuity--required-at-initial-launch).
- [ ] Separate visibly labeled thought cloud (evidence-based activity commentary) and
  speech bubble (visitor answer). Never expose internal reasoning. Idle and
  processing lines are grounded in observed state, free of inference, and never claim fake activity.
- [ ] Accessible responsive character interface with real availability,
  private member chat, queue status, draft preservation and offline fallback.
- [ ] Local Qwen3-14B benchmark; no public model API, tool access or home listener.
- [ ] Netlify static frontend, authenticated mailbox and outbound-only NucBox
  bridge; Guardian, review, quotas, bounded queues and emergency stop retained.
- [ ] Verified vault: lifetime net commercial receipts, expenses and current
  reviewed cash separately. Opening target $0 for new activity; do not publish
  zero as an observed balance without reconciliation. Historical Maker
  equipment is a separate inventory, never an invented debt or operating cash.
- [ ] Reward ladder combines real and humorous goals ($1 outfit, $10 fan,
  $50 community choice, $5,000 computer, $10,000 GPU fund, $1M collectible
  reactor). Thresholds unlock eligibility, not spending. Verified receipts,
  refunds, actual affordability and Maker approval govern purchase; evidence
  and redacted photographs distinguish fulfillment from unlock.
- [ ] Public Command Center: hourly bounded task selection, reviewed work-board
  projection, actual daily standup and community suggestion intake. See
  [community work board contract](COMMUNITY_BOARD.md). No separate scheduler.
- [ ] Penny's Workshop: Maker-approved beta previews, authenticated community
  feedback and bounded revisions, version history, verified contributor credit,
  independent quality and final commercial approval. Private Maker review UI
  required; see [community Workshop](COMMUNITY_WORKSHOP.md).
- [ ] Every Penny-created product and public beta carries Penny's approved
  character artwork, recognizable name/brand and accurate attribution; branded
  deliverable and listing are mandatory commercial release gates. See
  [product brand contract](PRODUCT_BRAND.md).
- [ ] Public diary, actual wins/setbacks, hardware changes and consented
  contributor credit; approved changes to Penny's room and wardrobe.
- [ ] One legitimate zero-additional-spend business experiment: hypothesis,
  approval, actual costs, outcome and community input. No invented revenue.
- [ ] Private business worker isolated from public chat; proposes changes only.
  Hermes is a candidate, not a public endpoint or trusted security boundary.
- [ ] Private end-to-end rehearsal and adversarial tests; explicit Maker
  authorization before live launch. Social content is optional later.

## Planned life and office progression (after core operational launch)
Maker-approved direction; do not delay the current kiosk, first business cycle,
hourly planner or secure website connection to implement these enhancements.
- [ ] Persistent office inventory and wishlist: start modestly, add virtual
  furnishings and achievement displays only from verified fulfillment records.
  Distinguish free digital rewards from actual purchases and compute upgrades.
- [ ] Penny's Office Collection: daily approved shirt and programmer-humor
  mug variants, persistent design IDs, accessible inspection and future
  reviewed merchandise listings with separate accounting. No initial live
  sales. See [office collection](OFFICE_COLLECTION.md).
- [ ] Configurable eight-hour off-duty period (proposed midnight–8 AM Eastern).
  Drain active work safely; no new business or chat generation while asleep.
  Essential services, backups and bounded message intake remain available.
- [ ] Optional fictional Dream Mode: sleeping scene plus random curated
  entertainment, clearly labeled as fiction. No business state changes, private
  data, memory promotion, inference triggered by viewing, or fictional earnings.
- [ ] Actual bedtime and morning reports, wake countdown, safe recovery and
  daylight-saving tests. See [life-cycle contract](PENNY_LIFE.md).

## State and release rules
Thought: evidence-based commentary on observed work, verified results and setbacks,
distinct from speech. No invented progress, rotating fictional commentary or
claims of learning without independent evidence review. Facial expressions are
symbolic responses to actual operational state, not consciousness. Keep failed
outcomes and missed targets; lessons require reviewed evidence.
Permanent personality: witty, snarky, humorous and an eternal optimist about
her million-dollar mission. Optimism means determination, not guaranteed results.
Humor targets her own situation, not supporters; never conceal bad news.
Speech: private draft -> exact-output review -> authorized delivery.
Idle/queued/working/answered/error are UI states driven by actual service status;
a demo must be labeled and must not send or store messages. No fabricated typing.
Milestones: planned -> eligible -> approved -> fulfilled (or withdrawn).
Room/wardrobe changes require approved verified fulfillment. Keep financial
and identity authority outside the model. Preserve existing quota and review
rules rather than replacing them with provisional UI limits. Final artwork,
purchase amounts, metric definitions and production configuration need review.

## Retained implementation contracts

# MVP / Definition of Done
Scope agreed; implementation pending. Detailed configuration thresholds remain provisional.

## A. Private core
- [ ] Benchmark Qwen3-14B quantized on a 16 GB GPU: 8192 context initial target, full GPU residency, measured throughput and stability. No paid inference.
- [ ] FastAPI backend, PostgreSQL durable state, replaceable local inference adapter, Docker portable deployment. Netlify-hosted public UI and native Netlify Database mailbox; outbound-only NucBox bridge. See [deployment contract](NETLIFY_BRIDGE.md). No public home-network listener.
- [ ] Bounded durable scheduler, verified priorities, transactional transitions, recovery, deadlines; non-LLM status.
- [ ] Versioned identity, canonical artwork and controlled expressions; final artwork and voice require approval.
- [ ] Immutable identity boundary and model-upgrade personality regression gates; evidence-backed contributor appreciation and consented recognition; see [identity and recognition contract](IDENTITY_AND_RECOGNITION.md).
- [ ] Consent-controlled personal memory and evidence-backed business learning; no untrusted policy mutation.
- [ ] Independent Guardian, approved tools, isolated development, no unrestricted shell or payment credentials.
- [ ] Balanced Vault and separate Founder Ledger. Actual startup costs only; no fabricated balances. Mixed revenue allocation pending approval.
- [ ] Restore drill and portable migration manifest; bounded logs and backups; secrets excluded.

## B. Private end-to-end
- [ ] Individual asynchronous chat, opt-in follow-ups and private reply delivery.
- [ ] Community proposals and votes influence real decisions; traceable evidence and explanations, opt-in credit.
- [ ] Business workflow researches, prototypes, tests and measures outcomes within approved limits.
- [ ] Mobile-first game-style Penny home scene, private dialogue bubble and question input, Achievement Center, greatest contributors showcase, World, Inbox, Council, Vault, diary, ventures, wishlist, member impact and actual availability. See [game UI contract](GAME_UI.md).
- [ ] Growth milestones represent verified progress; no fabricated life events or finances.
- [ ] Public Life Dashboard, historical metrics, upgrade comparisons and complete sanitized progress timeline including setbacks and recoveries; see [public progress contract](PUBLIC_PROGRESS.md).
- [ ] Evidence-backed, cached public read model with freshness, correction history, opt-in attribution and no inference calls for browsing.
- [ ] Payment sandbox, verified events, refunds, expiry and replay protection. No live funds yet.

## C. Public launch gate
- [ ] Separate external hosting, TLS, authenticated endpoints, edge defense, application quotas, private inference and database.
- [ ] Load and adversarial tests: caps, priorities, starvation, restart, injection, cross-member privacy, forged entitlements, memory poisoning, runaway tools.
- [ ] No automatic paid scaling; enforce costs outside model; public status works while queue closed.
- [ ] Accounting and payment-provider/legal review, pricing approval and final founder authorization.
- [ ] No public access to the founder's personal network.

## Workflow
Objective -> state/schema -> pseudocode -> implementation -> unit/integration tests. Meaningful structured logging, exception handling at boundaries, no private content in logs by default. Split modules exceeding 150 lines. No claimed test passes without execution.
