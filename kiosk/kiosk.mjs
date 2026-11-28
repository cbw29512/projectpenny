// Display only durable state; no AI requests, innerHTML, writes or fake progress.
const set = (id, value) => { document.getElementById(id).textContent = value; };
const stamp = value => new Date(value * 1000).toLocaleString();
import { reaction, expressions } from "./emotion.mjs";
import { validSnapshot, feedState, nextFeedOffset } from "./state.mjs";
function showReaction(s) {
  const {emotion, comment} = reaction(s);
  const [brows, mouth] = expressions[emotion];
  document.getElementById("brows").setAttribute("d", brows);
  document.getElementById("mouth").setAttribute("d", mouth);
  document.getElementById("mouth").setAttribute("fill", emotion === "celebrating" ? "#974d4b" : "none");
  set("emotion", "Expression: " + emotion);
  set("aside", comment);
}

let feedSignature = null;
let lastAdvance = 0;
function updateFeed(recent) {
  const state = feedState(feedSignature,recent);
  const window = document.getElementById("feed-window");
  if (!state.changed) return;
  feedSignature = state.signature;
  const list = document.getElementById("history");
  list.replaceChildren(...state.rows.map(item => {
    const li = document.createElement("li");
    li.textContent = stamp(item.finished_at) + " · " + (item.title ?? item.kind) + " — " + item.status;
    return li;
  }));
  if (!state.rows.length) {
    const li = document.createElement("li");
    li.textContent = "No recorded business activity";
    list.append(li);
  }
  window.scrollTop = 0;
  lastAdvance = Date.now();
  set("feed-position", state.rows.length + " recent tasks");
}
function advanceFeed() {
  if (document.body.dataset.offline !== "false" || Date.now()-lastAdvance < 8000) return;
  const window = document.getElementById("feed-window");
  const next = nextFeedOffset(window.scrollTop,window.scrollHeight,window.clientHeight);
  window.scrollTo({top:next,behavior:next===0?"instant":"smooth"});
  lastAdvance = Date.now();
}
setInterval(advanceFeed,1000);

function render(s) {
  document.body.dataset.offline = "false";
  set("health", "LIVE · LOCAL");
  set("updated", stamp(s.sampled_at));
  showReaction(s);
  const currency = new Intl.NumberFormat("en-US", {style:"currency",currency:"USD"});
  const finance = s.finance;
  for (const [id,key] of [["receipts","net_receipts"],["expenses","expenses"],["cash","recorded_cash"],["support","community_support"]]) {
    set(id, finance ? currency.format(finance[key]/100) : "Unverified");
  }
  set("finance-status", finance ? "Recorded ledger totals · not reconciled cash or spending authority" : "No Penny financial entries available");
  const m = s.latest_measurement;
  set("measurement", m ? m.title + " · " + m.measured_count + " / " + m.target + " · " + m.metric + " · " + stamp(m.recorded_at) : "No measurement recorded");
  set("done", s.counts.succeeded ?? 0);
  set("queue", s.counts.queued ?? 0);
  let activity = "Idle — no eligible work running";
  let detail = "";
  let elapsed = "";
  if (s.active) {
    const expired = s.active.lease_until <= s.sampled_at;
    activity = expired ? "Interrupted — review required" : "Task in progress";
    detail = s.active.title ?? s.active.kind;
    elapsed = Math.max(0, s.sampled_at - s.active.started_at) + " seconds elapsed";
  } else if (s.visitor_busy) {
    activity = "Private visitor task in progress";
  } else if (s.uncertain) {
    activity = "Safety gate — inference state uncertain";
    detail = "Checking or awaiting recovery; no progress claimed.";
  } else if (s.paused || !s.enabled) {
    activity = "Paused — awaiting authorization";
  } else if (s.counts.queued) {
    activity = "Work queued";
  }
  set("activity", activity); set("detail", detail); set("elapsed", elapsed);
  set("plan", s.latest_plan ? s.latest_plan.outcome + " · " + stamp(s.latest_plan.recorded_at) : "No hourly decision recorded");
  const latest = s.recent[0];
  set("title", latest ? latest.title ?? latest.kind : "No result available");
  set("speech", latest ? latest.prototype ?? latest.hypothesis ?? ("Task " + latest.status + " — no staged output") : "");
  updateFeed(s.recent);
}

async function poll() {
  try {
    const response = await fetch("/api/state", {cache:"no-store", signal:AbortSignal.timeout(5000)});
    if (!response.ok) throw new Error("state unavailable");
    const state = await response.json();
    if (!validSnapshot(state, Math.floor(Date.now()/1000))) throw new Error("stale or invalid state");
    render(state);
  } catch {
    document.body.dataset.offline = "true";
    set("health", "OFFLINE / STALE");
    set("activity", "Live state unavailable");
    set("detail", "Last successful snapshot remains below; do not treat it as current.");
    set("elapsed", "");
    showReaction(null);
    set("finance-status", "STALE · last recorded totals, not current");
  } finally {
    setTimeout(poll, 2000);
  }
}
poll();
