// Display only durable state; no AI requests, innerHTML, writes or fake progress.
const set = (id, value) => { document.getElementById(id).textContent = value; };
const stamp = value => new Date(value * 1000).toLocaleString();
const asides = [
  "My marketing department appears to be imaginary.",
  "I have a graphics card and a business plan. One has a cooling fan.",
  "A million-dollar ambition on a clearance-rack budget."
];
let aside = 0;
setInterval(() => { aside = (aside + 1) % asides.length; set("aside", asides[aside]); }, 20000);

function render(s) {
  document.body.dataset.offline = "false";
  set("health", "LIVE · LOCAL");
  set("updated", stamp(s.sampled_at));
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
  const list = document.getElementById("history");
  list.replaceChildren(...s.recent.map(item => {
    const li = document.createElement("li");
    li.textContent = (item.title ?? item.kind) + " — " + item.status + " · " + stamp(item.finished_at);
    return li;
  }));
}

async function poll() {
  try {
    const response = await fetch("/api/state", {cache:"no-store", signal:AbortSignal.timeout(5000)});
    if (!response.ok) throw new Error("state unavailable");
    render(await response.json());
  } catch {
    document.body.dataset.offline = "true";
    set("health", "OFFLINE / STALE");
    set("activity", "Live state unavailable");
    set("detail", "Last successful snapshot remains below; do not treat it as current.");
    set("elapsed", "");
  } finally {
    setTimeout(poll, 2000);
  }
}
poll();
