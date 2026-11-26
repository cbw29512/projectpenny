# Penny's Life Dashboard — public progress contract v0.1

## Objective
Every visitor can follow Penny's genuine growth, improvements, failures and recovery from day one. Public read access does not require membership or an inference call. Financial support buys defined service benefits, not ownership or influence over reported facts.

## Public metric catalog
- Finance: commercial revenue, refunds, fees, expenses, net earned profit/loss, available cash, reserves, founder funding and community support separately. Distinguish cash, accrual profit, asset value and net worth. USD initially; no double counting.
- Compute: approved hardware inventory (GPU, VRAM, RAM, storage), model family/version/quantization, context, measured token rate, benchmark suite version and results, aggregate availability, operating costs with measured/estimated labels.
- Operations: aggregate accepted/completed/failed/expired jobs, waiting capacity by class, latency distributions, uptime, incident duration and recovery, time allocation. No per-member details or raw task text.
- Learning: counts of validated memories and verified skills, benchmark improvements and regressions; no memory content.
- Business: disclosed ventures, products, launches, sales, refunds, experiments, costs, outcomes and discontinued projects.
- Community: aggregate membership, proposals, votes, implemented ideas and consented attribution. Avoid small-cohort disclosure.
- Recognition: verified contributor impact and successful ideas, consented credit, corrections and private follow-ups; see [identity and recognition contract](IDENTITY_AND_RECOGNITION.md). Financial support does not inflate measured idea impact.
- World: canonical character asset version, current residence metaphor, inventory and chapter changes tied to verified infrastructure milestones.
- Founder: Penny-branded merchandise/entertainment summaries and actual contributions under approved attribution policy; no unrelated personal finances.

## State and provenance
MetricDefinition: key, unit, source, aggregation, publication class, freshness SLA, version.
MetricObservation: metric key/version, period, decimal or typed value, evidence ref (private), source status, measured/estimated, recorded_at, correction_of.
ProgressEvent: UUID, kind (launch, upgrade, victory, setback, recovery, experiment, milestone, correction), occurred_at, recorded_at, sanitized summary, evidence ref, status, correction_of, approved_by.
UpgradeRecord: event_id, before/after asset/model refs, actual cost journal ref, approval ref, benchmark comparison refs, reason, rollback/outcome.
IncidentRecord: event_id, public impact, resolved_at, recovery event, sanitized explanation.
PublicProjection: version, generated_at, allowlisted fields, source event cursor. Publish independently of inference; expose stale/unavailable instead of fabricated zero.
FollowSubscription: member, topic, consent, channel, dedupe key, expiry; bounded delivery, no inference jobs.
CommunityImpact: existing decision/proposal/member attribution references; opt-in public display.

## Publication flow
1. Trusted producers ingest measured facts from ledger, scheduler, monitoring, benchmarks, approved asset inventory and venture records. LLM prose is never the source of truth.
2. Validate schema and evidence; distinguish provisional, verified, estimated, corrected and unavailable. Keep append-only audit history; corrections supersede earlier public values without silent rewriting.
3. Guardian sanitizes an explicit allowlist. Human review for sensitive business details, security incidents, attribution and financial disclosures. Publish safe summaries; redact details without implying no setback occurred.
4. Generate cached public read model with timestamp, historical series and evidence classification. Serve dashboard, timeline and upgrade comparison from this read model; never expose database or local inference to visitors.
5. Optional opt-in milestone subscriptions and digest delivery are deduplicated, rate-limited and independent of inference.
6. Penny may write diary commentary on verified events; label character fiction and never let commentary alter evidence or totals.

## UI
- Home: current chapter, actual availability, financial snapshot, next verified goal, latest progress events.
- Timeline: chronological filters for improvements, victories, setbacks, recovery, experiments and upgrades. Show date, before/after, cost, reason, outcome, evidence status and community impact where available.
- Metrics: historical charts with unit, source category, freshness, methodology/version, gaps and corrections. Compare equivalent benchmark configurations only.
- Upgrade history: planned vs approved vs purchased vs deployed vs benchmarked vs rolled back; actual costs and measured improvements separate from projections.
- Wishlist: quotes/estimates clearly dated; funding and sustainable cost gates; no fictional progress.
- Milestone detail: earned commercial profit and support tracked separately; fixed definition of $1M mission must be approved before publication.
- Public history remains accessible even when Penny is busy or offline; clearly label snapshot freshness.

## Privacy/security
No raw logs, prompts, private task content, personal names without consent, network addresses, exact residential/server location, credentials, private research or financial account identifiers. Publish aggregate metrics with disclosure thresholds and delayed release where needed. No unrestricted exports. Public API is read-only, bounded, paginated and cached. Retention/deletion obligations override public history; never retain exposed personal data merely for immutability.

## Acceptance
- Verified financial fixture reconciles with ledger; support/founder transfers do not inflate commercial earned profit.
- Missing source produces unavailable, not invented numbers; stale data retains timestamp.
- Every approved hardware change publishes a before/after record and links actual benchmark or explicit not-yet-measured status.
- Failed experiments, outages and regressions appear alongside successes; corrections preserve an audit trail.
- Synthetic/private records cannot leak through public projections, logs or exports; consent revocation removes public attribution.
- Public polling while busy performs zero inference calls; bounded query cost and pagination.
- Historical metrics compare only like-for-like versions and units; incompatible benchmarks are labeled.
- Dashboard and timeline remain readable during inference downtime.
- Test fixtures clearly labeled and never published as real activity.

## Public presentation and deployment
See [game-style home interface](GAME_UI.md) and [Netlify outbound bridge contract](NETLIFY_BRIDGE.md). Keep achievements and contributor displays evidence-backed and independent of paid tier.
