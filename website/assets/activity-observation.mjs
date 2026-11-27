// Older activity is historical observation, never live chat or sleep authority.
const STATES=Object.freeze({
  idle:"Idle",working:"Working",draining:"Finishing work",paused:"Paused",
  blocked:"Recovery required",off_duty:"Off duty"
});
export function observationView(raw,now){
  try{
    if(!Number.isSafeInteger(now)||!raw||typeof raw!=="object"||Array.isArray(raw)
       ||Object.keys(raw).length!==2||!Object.hasOwn(raw,"sampled_at")||!Object.hasOwn(raw,"activity")
       ||!Number.isSafeInteger(raw.sampled_at)||raw.sampled_at<=0||raw.sampled_at>now
       ||now-raw.sampled_at>=120||!Object.hasOwn(STATES,raw.activity))return null;
    return Object.freeze({label:"Last observed: "+STATES[raw.activity],sampledAt:raw.sampled_at});
  }catch{return null;}
}
