import { pajamasFor } from "./office-pajamas.mjs";
const ZONE="America/New_York";
const formatter=new Intl.DateTimeFormat("en-CA",{timeZone:ZONE,year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"});
export function easternParts(seconds){
  try{
    if(!Number.isSafeInteger(seconds)||seconds<Date.UTC(2000,0,1)/1000||seconds>=Date.UTC(2100,0,1)/1000)return null;
    const p=Object.fromEntries(formatter.formatToParts(seconds*1000).map(x=>[x.type,x.value]));
    return {date:p.year+"-"+p.month+"-"+p.day,hour:Number(p.hour),minute:Number(p.minute),second:Number(p.second)};
  }catch{return null;}
}
// Snapshot consumer only: trusted server must actually enforce its rest gate.
// Device time can reject expired evidence, never create operational authority.
export function parseRest(text,now){
  try{
    if(typeof text!=="string"||text.length>2048||!Number.isSafeInteger(now))return null;
    const s=JSON.parse(text);
    const keys=["schema","status","policy","state","sampled_at","expires_at","wake_at","gate_closed","active"];
    if(!s||typeof s!=="object"||Array.isArray(s)||Object.keys(s).length!==keys.length
      ||!keys.every(k=>Object.hasOwn(s,k))||s.schema!=="penny-rest-v1"||s.status!=="reviewed"
      ||s.policy!=="rest-concept-v1"||!["awake","draining","asleep","blocked"].includes(s.state)
      ||!Number.isSafeInteger(s.sampled_at)||!Number.isSafeInteger(s.expires_at)
      ||s.sampled_at>now||now>=s.expires_at||s.expires_at-s.sampled_at>60
      ||typeof s.gate_closed!=="boolean"||typeof s.active!=="boolean")return null;
    const p=easternParts(s.sampled_at);
    if(!p)return null;
    if(s.state==="asleep"){
      const wake=easternParts(s.wake_at);
      if(!s.gate_closed||s.active||p.hour>=8||!wake||wake.date!==p.date
        ||wake.hour!==8||wake.minute!==0||wake.second!==0||s.wake_at<=now
        ||s.expires_at>s.wake_at)return null;
    }else if(s.wake_at!==null)return null;
    return Object.freeze({state:s.state,date:p.date,wakeAt:s.wake_at,sampledAt:s.sampled_at});
  }catch{return null;}
}
export function nightView(rest,now){
  try{
    if(!rest||rest.state!=="asleep")return null;
    const pajamas=pajamasFor(rest.date);
    if(!pajamas||rest.wakeAt<=now)return null;
    return {pajamas,minutes:Math.ceil((rest.wakeAt-now)/60)};
  }catch{return null;}
}
