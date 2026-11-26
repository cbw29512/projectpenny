// Cache envelope matches the reviewed local Python snapshot, not model output.
const FINANCE = ["commercial_receipts","commercial_refunds","community_support",
  "founder_cash_funding","founder_paid_costs","operating_expenses","payment_fees",
  "commercial_result_after_recorded_costs","matched_cash","statement_at"];
const BUSINESS = ["proposed","approved","started","overdue","expired","rejected",
  "stopped","measured_target_met","measured_target_missed"];
const MAX = 9000000000000000;
const MAX_TIME = 253402300799;
const unavailable = () => ({status:"unavailable",generatedAt:null,expiresAt:null,finance:null,business:null});

function exact(value,keys) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === keys.length
    && keys.every(k => Object.hasOwn(value,k));
}
const bounded = n => Number.isSafeInteger(n) && Math.abs(n)<=MAX;
const timestamp = n => Number.isSafeInteger(n) && n>0 && n<=MAX_TIME;

function section(data,keys) {
  if (data===null) return null;
  if (!exact(data,keys)) throw new Error("invalid metric section");
  const result={};
  for (const k of keys) {
    const n=data[k];
    if (!bounded(n) || (k!=="commercial_result_after_recorded_costs" && n<0))
      throw new Error("invalid metric value");
    result[k]=n;
  }
  return result;
}

export function progressState(raw,now) {
  try {
    if (!timestamp(now)) return unavailable();
    if (exact(raw,["status","payload"]) && raw.status==="unavailable" && raw.payload===null)
      return unavailable();
    if (!exact(raw,["status","version","generated_at","expires_at","payload"])
      || !["reviewed","stale"].includes(raw.status) || !bounded(raw.version) || raw.version<1
      || !timestamp(raw.generated_at) || !timestamp(raw.expires_at)
      || raw.expires_at<=raw.generated_at || raw.expires_at-raw.generated_at>3600
      || now<raw.generated_at) return unavailable();
    const timing={generatedAt:raw.generated_at,expiresAt:raw.expires_at};
    if (raw.status==="stale") {
      return raw.payload===null ? {...unavailable(),...timing,status:"stale"} : unavailable();
    }
    if (now>=raw.expires_at) return {...unavailable(),...timing,status:"stale"};
    const p=raw.payload;
    if (!exact(p,["schema","finance","business"]) || p.schema!=="penny-progress-v1")
      return unavailable();
    const finance=section(p.finance,FINANCE);
    const business=section(p.business,BUSINESS);
    if (finance!==null && (!timestamp(finance.statement_at)
      || finance.statement_at>raw.generated_at
      || raw.expires_at>finance.statement_at+86400)) return unavailable();
    return {status:"reviewed",...timing,finance,business};
  } catch {
    return unavailable();
  }
}

export function parseProgress(text,now) {
  try {
    if (typeof text!=="string" || text.length>8192) return unavailable();
    return progressState(JSON.parse(text),now);
  } catch { return unavailable(); }
}

export function usd(cents) {
  if (!bounded(cents)) return "Unavailable";
  // Integer arithmetic retains exact cents even near the safe-integer limit.
  const amount=BigInt(cents);
  const absolute=amount<0n?-amount:amount;
  return (amount<0n?"-":"")+"$"+(absolute/100n).toLocaleString("en-US")+"."
    +(absolute%100n).toString().padStart(2,"0");
}

export function metricText(state,scope,key) {
  if (state.status!=="reviewed" || !["finance","business"].includes(scope))
    return "Unavailable";
  const section=state[scope];
  if (!section || !Object.hasOwn(section,key)) return "Unavailable";
  return scope==="finance"?usd(section[key]):section[key].toLocaleString("en-US");
}
