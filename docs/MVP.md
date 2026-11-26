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
