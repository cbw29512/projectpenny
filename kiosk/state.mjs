// Reject stale or malformed runtime evidence before presenting it as live.
export function validSnapshot(s, now) {
  try {
    const integer = n => Number.isSafeInteger(n) && n >= 0;
    const record = v => v !== null && typeof v === "object" && !Array.isArray(v);
    if (!record(s) || !integer(now) || !integer(s.sampled_at)
        || s.sampled_at > now + 2 || now - s.sampled_at > 10) return false;
    if (!["paused","enabled","uncertain","visitor_busy"].every(k => typeof s[k] === "boolean")) return false;
    if (!record(s.counts) || !Object.values(s.counts).every(integer)) return false;
    if (!Array.isArray(s.recent) || s.recent.length > 5
        || !s.recent.every(r => record(r) && integer(r.finished_at)
          && r.finished_at <= s.sampled_at && typeof r.status === "string")) return false;
    if (s.active !== null && (!record(s.active) || !integer(s.active.started_at)
        || !integer(s.active.lease_until) || s.active.started_at > s.sampled_at)) return false;
    if (s.latest_plan !== null && (!record(s.latest_plan)
        || !integer(s.latest_plan.recorded_at) || s.latest_plan.recorded_at > s.sampled_at
        || typeof s.latest_plan.outcome !== "string")) return false;
    const m = s.latest_measurement;
    if (m !== null && (!record(m) || !integer(m.recorded_at) || m.recorded_at > s.sampled_at
        || !integer(m.measured_count) || !integer(m.target) || m.target === 0)) return false;
    const money = s.finance;
    if (money !== undefined && money !== null && (!record(money)
        || money.status !== "recorded_unreconciled"
        || !["net_receipts","expenses","recorded_cash","community_support"].every(k => Number.isSafeInteger(money[k])))) return false;
    return true;
  } catch {
    return false;
  }
}
