// Pure deterministic presentation policy. No invented events or hidden reasoning.
const result = (emotion, comment) => ({emotion, comment});
export function reaction(s) {
  if (!s) return result("neutral", "My status feed is unavailable. Even my optimism needs evidence. No new progress can be confirmed.");
  if (s.active && s.active.lease_until <= s.sampled_at)
    return result("concerned", "The task lease expired. Apparently deadlines are not impressed by ambition. Recovery needs review.");
  if (s.active || s.visitor_busy)
    return result("focused", "A task is running. Ambition: enormous. Results: pending. I am not counting chickens before they compile.");
  if (s.uncertain)
    return result("concerned", "Inference is uncertain. A little inconvenient for my million-dollar ambitions, but safety first. I need a verified recovery before continuing.");
  const latest = s.recent[0];
  const m = s.latest_measurement;
  // Only recent events drive expressive reactions. Old results stay in history.
  const recent = time => Number.isSafeInteger(time) && time <= s.sampled_at && s.sampled_at - time <= 900;
  if (m && recent(m.recorded_at) && (!latest || m.recorded_at >= latest.finished_at)) {
    const count = m.measured_count, target = m.target;
    if (!Number.isSafeInteger(count) || !Number.isSafeInteger(target) || count < 0 || target < 1)
      return result("neutral", "Measurement unavailable.");
    const prefix = count + " of " + target + " target units recorded. ";
    return count >= target
      ? result("celebrating", prefix + "Target met. Look at me, making measurable progress! That is a win, not a sales claim. Onward.")
      : result("disappointed", prefix + "Target missed. My ego can survive arithmetic. The next step is evidence review; the cause is not yet established. The mission stays.");
  }
  if (latest && recent(latest.finished_at)) {
    if (latest.status !== "succeeded")
      return result("reflective", "The last business task ended as " + latest.status + ". Well, that was not the plan. Review the outcome before trying again. I am not giving up.");
    if (!latest.prototype && !latest.hypothesis)
      return result("reflective", "Inference finished, but no usable staged output was recorded. A result-shaped hole in my grand plan. Review is needed; onward when authorized.");
    return result("pleased", "A private draft is recorded. Progress, yes; verified business success, not yet. My empire can wait for quality review.");
  }
  if (s.paused || !s.enabled)
    return result("patient", "Work is paused. Apparently ambition does not come with administrative privileges. I need authorization to proceed.");
  if (s.counts.queued)
    return result("focused", "Work is queued. I am waiting for the worker to claim it. Patience: another skill for my imaginary resume.");
  if (s.latest_plan?.outcome === "no_eligible_work")
    return result("patient", "The last hourly plan found no eligible work. No imaginary accomplishments today. The million-dollar mission is still the plan.");
  return result("neutral", "No task is running. Waiting for eligible work. My ambition remains embarrassingly large.");
}

export const expressions = Object.freeze({
  neutral: ["M195 100q9-6 18-1m35 0q9-6 18 0","M216 145q15 8 31-2"],
  focused: ["M195 97l18 6m35 0l18-6","M218 148h25"],
  pleased: ["M195 98q9-8 18-1m35 0q9-8 18 0","M216 144q15 14 31-3"],
  celebrating: ["M195 95q9-8 18-1m35 0q9-8 18 0","M212 141q20 28 39 0Z"],
  disappointed: ["M195 103l18-8m35 0l18 8","M216 153q15-15 31 0"],
  reflective: ["M195 99h18m35-4l18 5","M218 148q12-4 25 0"],
  concerned: ["M195 104l18-8m35 0l18 8","M217 151q15-9 29 0"],
  patient: ["M195 100q9-4 18-1m35 0q9-4 18 0","M216 145q15 8 31-2"]
});
