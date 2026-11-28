import {createHmac,timingSafeEqual} from "node:crypto";
import {exact} from "../gateway/state.mjs";
const STATES=new Set(["idle","working","draining","paused","blocked","off_duty"]);
const DOMAIN="penny-activity-publish-v1.";
export function sampleValid(value,now,maxAge){
  return exact(value,["sampled_at","activity"])&&Number.isSafeInteger(now)
    &&Number.isSafeInteger(value.sampled_at)&&value.sampled_at>0
    &&value.sampled_at<=now&&now-value.sampled_at<maxAge&&STATES.has(value.activity);
}
export function createActivityVerifier(key){
  if(!Buffer.isBuffer(key)||key.length<32||key.length>64)throw Error("invalid projection key");
  const secret=Buffer.from(key);
  return (header,value,now)=>{
    try{
      if(typeof header!=="string"||!/^PennyActivity v1\.[0-9a-f]{64}$/.test(header)
         ||!sampleValid(value,now,15))return false;
      const expected=createHmac("sha256",secret)
        .update(DOMAIN+value.sampled_at+"."+value.activity).digest();
      return timingSafeEqual(Buffer.from(header.slice("PennyActivity v1.".length),"hex"),expected);
    }catch{return false;}
  };
}
