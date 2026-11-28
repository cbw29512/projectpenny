// Private beta client protocol: never infer delivery from a failed request.
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export const isId=x=>typeof x==="string"&&UUID.test(x)&&x!=="00000000-0000-0000-0000-000000000000";
export const validText=(x,n)=>typeof x==="string"&&x.trim().length>0
  &&Array.from(x).length<=n&&!x.includes("\0")&&!/[\uD800-\uDFFF]/u.test(x);
const exact=(x,keys)=>x!==null&&typeof x==="object"&&!Array.isArray(x)
  &&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const READ=new Set(["submitted","claimed","locally_accepted","answered","rejected","expired"]);
const DENIED=new Map([[400,["invalid"]],[401,["unauthorized"]],[403,["denied"]],
  [409,["conflict","member_busy"]],[429,["rate_limited","member_quota","community_quota"]],
  [503,["paused","full"]],[413,["invalid"]],[415,["invalid"]]]);
export function decodeReceipt(code,data){
  try{
    if(code===202&&exact(data,["status","id","replayed"])&&data.status==="accepted"
        &&isId(data.id)&&typeof data.replayed==="boolean")
      return {status:"accepted",id:data.id,replayed:data.replayed};
    if(exact(data,["status"])&&DENIED.get(code)?.includes(data.status))
      return {status:data.status};
    return {status:"uncertain"};
  }catch{return {status:"uncertain"};}
}
export function decodeRead(code,data,id){
  try{
    if(code===200&&exact(data,["id","status","text"])&&data.id===id&&READ.has(data.status)
      &&(data.status==="answered"?validText(data.text,16000):data.text===null))
      return {status:data.status,text:data.text};
    if(code===404&&exact(data,["status"])&&data.status==="not_found")return {status:"not_found"};
    if(exact(data,["status"])&&DENIED.get(code)?.includes(data.status))return {status:data.status};
    return {status:"unavailable"};
  }catch{return {status:"unavailable"};}
}
export const terminal=s=>["answered","rejected","expired","not_found"].includes(s);
