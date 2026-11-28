// No free text, URLs or identity data accepted from the candidate.
const COPY=Object.freeze({
  idle:["Idle · local worker","No task is running. My ambition remains embarrassingly large."],
  working:["Working","A task is running. Results are pending; ambition is not a receipt."],
  draining:["Finishing work","Finishing existing work before scheduled rest."],
  paused:["Paused","Work is paused. Apparently ambition requires authorization."],
  blocked:["Recovery required","Work requires verified recovery. No new result can be confirmed."],
  off_duty:["Off duty","Scheduled rest. No new task is running."],
  unavailable:["Live AI not connected","No current verified activity is available."]
});
export function activityView(text,now){
  try{
    if(typeof text!=="string"||text.length>1024||!Number.isSafeInteger(now))return COPY.unavailable;
    const s=JSON.parse(text),keys=["schema","status","state","sampled_at","expires_at"];
    if(!s||typeof s!=="object"||Array.isArray(s)||Object.keys(s).length!==keys.length
      ||!keys.every(k=>Object.hasOwn(s,k))||s.schema!=="penny-activity-v1"||s.status!=="reviewed"
      ||!Object.hasOwn(COPY,s.state)||s.state==="unavailable"
      ||!Number.isSafeInteger(s.sampled_at)||s.sampled_at<=0||s.sampled_at>now
      ||!Number.isSafeInteger(s.expires_at)||s.expires_at-s.sampled_at!==15||now>=s.expires_at)
      return COPY.unavailable;
    return COPY[s.state];
  }catch{return COPY.unavailable;}
}
