import {createHmac,timingSafeEqual} from "node:crypto";
import {exact} from "../gateway/state.mjs";
const STAGES=new Set(["prototype_reviewed","preview_reviewed","revision_reviewed","review_withdrawn"]);
const DOMAIN="penny-workshop-publish-v1.";
export const unavailable=()=>({schema:"penny-workshop-v1",status:"unavailable"});
export function valid(value,now,maxAge){
  if(!exact(value,["sampled_at","stage","generated_at","expires_at"])
    ||![now,value.sampled_at,value.generated_at,value.expires_at].every(Number.isSafeInteger)
    ||value.sampled_at<=0||value.sampled_at>now||now-value.sampled_at>=maxAge)return false;
  if(value.stage==="unavailable")return value.generated_at===0&&value.expires_at===0;
  return STAGES.has(value.stage)&&value.generated_at>0&&value.generated_at<=value.sampled_at
    &&value.expires_at>now&&value.expires_at-value.sampled_at<=120
    &&value.expires_at-value.generated_at<=3600;
}
export function createWorkshopVerifier(key){
  if(!Buffer.isBuffer(key)||key.length<32||key.length>64)throw Error("invalid Workshop key");
  const secret=Buffer.from(key);
  return (header,value,now)=>{
    try{
      if(typeof header!=="string"||!/^PennyWorkshop v1\.[0-9a-f]{64}$/.test(header)
        ||!valid(value,now,15))return false;
      const expected=createHmac("sha256",secret).update(DOMAIN+
        [value.sampled_at,value.stage,value.generated_at,value.expires_at].join(".")).digest();
      return timingSafeEqual(Buffer.from(header.slice("PennyWorkshop v1.".length),"hex"),expected);
    }catch{return false;}
  };
}
export function browserView(value,now){
  if(!valid(value,now,120)||value.stage==="unavailable")return unavailable();
  return {schema:"penny-workshop-v1",status:"reviewed",product:"packing-checklist-v1",
    stage:value.stage,generated_at:value.generated_at,expires_at:value.expires_at};
}
