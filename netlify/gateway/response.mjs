// Only the explicit public/private wire fields may leave the gateway.
import {isId,isText} from "./state.mjs";
const STATUS={accepted:202,invalid:400,denied:403,conflict:409,
  paused:503,member_quota:429,community_quota:429,member_busy:409,full:503};
const STATES=new Set(["submitted","claimed","locally_accepted","answered","rejected","expired"]);
export function reply(status,body,retry) {
  const headers={"Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff",
    "Referrer-Policy":"no-referrer"};
  if(retry) headers["Retry-After"]=String(retry);
  return new Response(JSON.stringify(body),{status,headers});
}
export function resultResponse(op,row) {
  if(op==="submit") {
    if(!row || !Object.hasOwn(STATUS,row.status)) throw new Error("invalid receipt");
    if(row.status==="accepted") {
      if(!isId(row.question_id) || typeof row.replayed!=="boolean") throw new Error("invalid receipt");
      return reply(202,{status:row.status,id:row.question_id,replayed:row.replayed});
    }
    return reply(STATUS[row.status],{status:row.status},STATUS[row.status]===429?3600:undefined);
  }
  if(op==="read") {
    if(row===null) return reply(404,{status:"not_found"});
    if(!isId(row.question_id) || !STATES.has(row.status) ||
       (row.status==="answered" ? !isText(row.reply,16000) : row.reply!==null))
      throw new Error("invalid read");
    return reply(200,{id:row.question_id,status:row.status,text:row.reply});
  }
  if(op==="claim") {
    if(row===null) return reply(200,{status:"empty"});
    const expiry=new Date(row.lease_until);
    if(![row.question_id,row.owner_id,row.fence].every(isId) ||
       !isText(row.body,2000) || !Number.isFinite(expiry.getTime()))
      throw new Error("invalid claim");
    return reply(200,{status:"claimed",id:row.question_id,owner:row.owner_id,
      text:row.body,fence:row.fence,leaseUntil:expiry.toISOString()});
  }
  if(typeof row?.ok!=="boolean") throw new Error("invalid result");
  return reply(row.ok?200:409,{status:row.ok?"ok":"conflict"});
}
