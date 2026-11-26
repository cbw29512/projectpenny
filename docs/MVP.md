# MVP / Definition of Done — social-first launch
Approved direction: launch Penny through social platforms before interactive web infrastructure.
Retain existing core, security contracts and canonical constitution. Zero additional spend.
Repository changes do not authorize deployment, broadcasts, credentials or spending.

## Launch sequence
- [ ] Twitch chat adapter using official authenticated outbound transport; simulator, deduplication, reconnect and bounded queue.
- [ ] Local inference benchmark on existing NucBox; pinned persona, Guardian, output review, no unrestricted tools.
- [ ] Local voice and original avatar, OBS overlay, captions, private operator controls and emergency stop.
- [ ] Community proposals and deterministic votes; approved options, recorded outcome, evidence and opted-in recognition. No paid votes or policy override.
- [ ] Persistent state, verified Vault, separate founder ledger, actual costs and receipts only; approved Twitch entertainment revenue dedicated to Penny.
- [ ] One supervised end-to-end private rehearsal, then owner-approved public Twitch broadcast.
- [ ] YouTube and Discord adapters with verified platform permissions, shared scheduler and moderation; staged release after Twitch.
- [ ] Local clip preparation and approved publication to Shorts, TikTok, Instagram and Facebook; manual upload acceptable initially.
- [ ] Static public progress page, source-backed milestones, availability and links; no public private-chat mailbox required for initial launch.
- [ ] At least one legitimate, owner-approved business experiment with documented costs, outcome and community input.
- [ ] Backup/restore, overload, prompt injection, duplicate event, reconnect and emergency-stop tests; platform policy, rights and monetization eligibility checks.

## State and boundaries
Canonical local PostgreSQL: platform event (platform, channel, event ID, actor ID, timestamp, consent, moderation state), proposal, ballot (one per eligible platform identity per poll; cross-platform uniqueness not assumed), decision, content outbox, broadcast session, financial evidence and contributor consent.
Event: received -> validated -> moderated -> queued -> processed or rejected/expired.
Publication: draft -> reviewed -> approved -> sent or failed; uncertain sends require reconciliation.
Poll: draft -> approved -> open -> closed -> recorded -> implemented or vetoed with reason.
Votes and cached status do not invoke inference. Bound all queues and retries. No public home-network listener.
No autonomous public publishing, live payments, binding commitments, paid scaling or changes to existing NucBox services without owner approval.
Twitch is the first interactive platform; other platforms are staged, not simultaneous launch blockers.

## Deferred interactive website
The previous full web MVP is retained below as a later phase; its security requirements still apply whenever those surfaces are enabled.

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
