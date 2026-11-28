// Bit is fictional presentation, not a model, tool, worker or financial actor.
const MODES=Object.freeze({idle:"idle",working:"attentive",answering:"attentive",
  verified_sale:"celebrating",verified_achievement:"celebrating",
  error:"confused",asleep:"charging",unavailable:"idle"});
const EVENTS=new Set(["verified_sale","verified_achievement","error"]);
export function bitReaction(text, now) {
  try {
    if(typeof text!=="string"||text.length>1024||!Number.isSafeInteger(now))return "idle";
    const s=JSON.parse(text);
    const keys=["schema","status","activity","sampled_at","event_at"];
    if(!s||typeof s!=="object"||Array.isArray(s)||Object.keys(s).length!==keys.length
      ||!keys.every(k=>Object.hasOwn(s,k))||s.schema!=="penny-bit-activity-v1"
      ||s.status!=="reviewed"||!Object.hasOwn(MODES,s.activity)
      ||!Number.isSafeInteger(s.sampled_at)||s.sampled_at<=0
      ||s.sampled_at>now||now-s.sampled_at>=60)return "idle";
    if(EVENTS.has(s.activity)){
      if(!Number.isSafeInteger(s.event_at)||s.event_at<=0||s.event_at>s.sampled_at
        ||now-s.event_at>=15)return "idle";
    }else if(s.event_at!==null)return "idle";
    return MODES[s.activity];
  }catch{return "idle";}
}
