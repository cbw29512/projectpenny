// Public display contract: fixed labels only, no private identifiers or product bytes.
const LABELS=Object.freeze({
  prototype_reviewed:"A private prototype has passed a reviewed quality check.",
  preview_reviewed:"A preview has been reviewed. Access is not connected here.",
  beta_reviewed:"A beta edition has been reviewed. Tester delivery is not connected here.",
  revision_reviewed:"A product revision has a recorded improvement review.",
  review_withdrawn:"A previous product review has been withdrawn.",
});
const unavailable=()=>({status:"unavailable",stage:null,generatedAt:null,expiresAt:null});
const validTime=n=>Number.isSafeInteger(n)&&n>0&&n<=253402300799;
function exact(value,keys){
  return value!==null&&typeof value==="object"&&!Array.isArray(value)
    &&Object.keys(value).length===keys.length&&keys.every(k=>Object.hasOwn(value,k));
}
export function workshopState(raw,now){
  try{
    if(!validTime(now))return unavailable();
    if(!exact(raw,["schema","status","product","stage","generated_at","expires_at"])
      ||raw.schema!=="penny-workshop-v1"||raw.status!=="reviewed"
      ||raw.product!=="packing-checklist-v1"||typeof raw.stage!=="string"
      ||!Object.hasOwn(LABELS,raw.stage)||!validTime(raw.generated_at)
      ||!validTime(raw.expires_at)||raw.generated_at>now
      ||raw.expires_at<=raw.generated_at||raw.expires_at-raw.generated_at>3600)
      return unavailable();
    if(now>=raw.expires_at)return {...unavailable(),status:"stale"};
    return {status:"reviewed",stage:raw.stage,generatedAt:raw.generated_at,expiresAt:raw.expires_at};
  }catch{return unavailable();}
}
export function parseWorkshop(text,now){
  try{
    if(typeof text!=="string"||text.length>1024)return unavailable();
    return workshopState(JSON.parse(text),now);
  }catch{return unavailable();}
}
export function stageLabel(state){
  return state?.status==="reviewed"&&Object.hasOwn(LABELS,state.stage)
    ?LABELS[state.stage]:"Development status unavailable.";
}
