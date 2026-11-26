// The backend supplies reviewed state, never display text or arbitrary codes.
export const CODES=Object.freeze(["first_dollar","in_the_green","proof_of_concept"]);
const STATES=Object.freeze({
  unverified:"Unverified", verified:"Verified", withdrawn:"Withdrawn",
  needs_review:"Needs review",
});
const MAX_TIME=253402300799;
const timestamp=n=>Number.isSafeInteger(n)&&n>0&&n<=MAX_TIME;
const unavailable=()=>({status:"unavailable",achievements:[],expiresAt:null});
function exact(obj,keys) {
  return obj!==null&&typeof obj==="object"&&!Array.isArray(obj)
    &&Object.keys(obj).length===keys.length&&keys.every(k=>Object.hasOwn(obj,k));
}
export function achievementState(raw,now) {
  try {
    if(!timestamp(now)) return unavailable();
    if(exact(raw,["schema","status","achievements"])&&raw.schema==="penny-achievements-v1"
      &&raw.status==="unavailable"&&Array.isArray(raw.achievements)&&raw.achievements.length===0)
      return unavailable();
    if(!exact(raw,["schema","status","generated_at","expires_at","achievements"])
      ||raw.schema!=="penny-achievements-v1"||raw.status!=="reviewed"
      ||!timestamp(raw.generated_at)||!timestamp(raw.expires_at)
      ||raw.generated_at>now||raw.expires_at<=raw.generated_at
      ||raw.expires_at-raw.generated_at>3600||!Array.isArray(raw.achievements)
      ||raw.achievements.length!==CODES.length) return unavailable();
    if(now>=raw.expires_at) return {...unavailable(),status:"stale"};
    const seen=new Set(),achievements=[];
    for(const a of raw.achievements) {
      if(!exact(a,["code","status","review_day"])||!CODES.includes(a.code)
        ||seen.has(a.code)||typeof a.status!=="string"||!Object.hasOwn(STATES,a.status))
        return unavailable();
      if(a.status==="verified") {
        if(!Number.isSafeInteger(a.review_day)||a.review_day<0
          ||a.review_day>raw.generated_at||a.review_day%86400!==0) return unavailable();
      } else if(a.review_day!==null) return unavailable();
      seen.add(a.code);
      achievements.push({code:a.code,status:a.status,reviewDay:a.review_day});
    }
    return {status:"reviewed",achievements,expiresAt:raw.expires_at};
  } catch { return unavailable(); }
}
export function parseAchievements(text,now) {
  try {
    if(typeof text!=="string"||text.length>4096) return unavailable();
    return achievementState(JSON.parse(text),now);
  } catch { return unavailable(); }
}
export function awardDisplay(state,code) {
  const fallback={label:"Unverified",verified:false,date:""};
  try {
    if(state.status!=="reviewed"||!CODES.includes(code)) return fallback;
    const a=state.achievements.find(item=>item.code===code);
    if(!a||!Object.hasOwn(STATES,a.status)) return fallback;
    const verified=a.status==="verified";
    return {label:STATES[a.status],verified,date:verified?
      new Date(a.reviewDay*1000).toISOString().slice(0,10):""};
  } catch { return fallback; }
}
