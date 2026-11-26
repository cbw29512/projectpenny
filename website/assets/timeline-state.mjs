// Closed vocabulary: never render labels or arbitrary text from the envelope.
export const LABELS=Object.freeze({
  target_met:"Business experiment met its target.",
  target_missed:"Business experiment missed its target.",
  experiment_stopped:"Business experiment was stopped.",
  experiment_rejected:"Business experiment was not approved.",
  corrected:"A previously reviewed event was withdrawn.",
});
const FILTERS=Object.freeze({
  all:Object.keys(LABELS),
  victories:["target_met"],
  setbacks:["target_missed"],
  discontinued:["experiment_stopped","experiment_rejected"],
  corrections:["corrected"],
});
const MAX_TIME=253402300799;
const unavailable=()=>({status:"unavailable",events:[],generatedAt:null,expiresAt:null});
const time=n=>Number.isSafeInteger(n)&&n>0&&n<=MAX_TIME;
function exact(value,keys) {
  return value!==null&&typeof value==="object"&&!Array.isArray(value)
    &&Object.keys(value).length===keys.length&&keys.every(k=>Object.hasOwn(value,k));
}

export function timelineState(raw,now) {
  try {
    if (!time(now)) return unavailable();
    if (exact(raw,["schema","status","events"])&&raw.schema==="penny-timeline-v1"
        &&raw.status==="unavailable"&&Array.isArray(raw.events)&&raw.events.length===0)
      return unavailable();
    if (!exact(raw,["schema","status","events","generated_at","expires_at"])
        ||raw.schema!=="penny-timeline-v1"||raw.status!=="reviewed"
        ||!time(raw.generated_at)||!time(raw.expires_at)
        ||raw.generated_at>now||raw.expires_at<=raw.generated_at
        ||raw.expires_at-raw.generated_at>3600||!Array.isArray(raw.events)
        ||raw.events.length<1||raw.events.length>20) return unavailable();
    const timing={generatedAt:raw.generated_at,expiresAt:raw.expires_at};
    if (now>=raw.expires_at) return {...unavailable(),...timing,status:"stale"};
    let previous=raw.generated_at;
    const events=[];
    for (const item of raw.events) {
      if (!exact(item,["kind","day_epoch"])||typeof item.kind!=="string"
          ||!Object.hasOwn(LABELS,item.kind)||!Number.isSafeInteger(item.day_epoch)
          ||item.day_epoch<0||item.day_epoch>previous||item.day_epoch%86400!==0)
        return unavailable();
      previous=item.day_epoch;
      events.push({kind:item.kind,day:item.day_epoch});
    }
    return {status:"reviewed",events,...timing};
  } catch { return unavailable(); }
}

export function parseTimeline(text,now) {
  try {
    if (typeof text!=="string"||text.length>8192) return unavailable();
    return timelineState(JSON.parse(text),now);
  } catch { return unavailable(); }
}

export function filterEvents(state,filter) {
  try {
    if (state.status!=="reviewed"||!Object.hasOwn(FILTERS,filter)) return [];
    return state.events.filter(e=>FILTERS[filter].includes(e.kind)).map(e=>({
      kind:e.kind,label:LABELS[e.kind],date:new Date(e.day*1000).toISOString().slice(0,10),
    }));
  } catch { return []; }
}
