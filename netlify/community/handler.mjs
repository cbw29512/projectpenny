// Inactive HTTP candidate. Not registered with the production gateway.
import {exact,isId} from "../gateway/state.mjs";
import {boundedJson} from "../gateway/body.mjs";
import {reply} from "../gateway/response.mjs";
import {validateSuggestion,validateClaim} from "./state.mjs";

const routes=Object.freeze({
  "/api/v1/suggestions":{scope:"member",op:"submit",max:4096},
  "/api/v1/bridge/community/claim":{scope:"bridge",op:"claim",max:256},
  "/api/v1/bridge/community/ack":{scope:"bridge",op:"ack",max:1024}
});
const codes=Object.freeze({invalid:400,denied:403,conflict:409,expired:409,
  paused:503,member_quota:429,full:503});
const ascii=text=>typeof text==="string" && /^[ -~]+$/.test(text);
const epoch=value=>{
  if(!(value instanceof Date) && typeof value!=="string") throw new Error("invalid timestamp");
  const n=new Date(value).getTime();
  if(!Number.isFinite(n)) throw new Error("invalid timestamp");
  return Math.floor(n/1000);
};

export function createCommunityHandler({verify,limiter,repository,origin,
  enabled=false,now=()=>Math.floor(Date.now()/1000)}) {
  if(typeof verify!=="function" || typeof limiter!=="function" ||
     typeof origin!=="string" || new URL(origin).origin!==origin ||
     !origin.startsWith("https://") ||
     !["submit","claim","ack"].every(k=>typeof repository?.[k]==="function"))
    throw new TypeError("community dependencies incomplete");
  return async request=>{
    try {
      if(enabled!==true) return reply(503,{status:"paused"},60);
      const url=new URL(request.url);
      if(url.origin!==origin || url.search) return reply(400,{status:"invalid"});
      if(request.method!=="POST" || !Object.hasOwn(routes,url.pathname))
        return reply(404,{status:"not_found"});
      const {scope,op,max}=routes[url.pathname];
      const source=request.headers.get("origin");
      if(source!==null && source!==origin) return reply(403,{status:"denied"});
      const identity=verify(request.headers.get("authorization"),scope);
      if(identity?.scope!==scope || (scope==="member"?!isId(identity.subject):
         identity.subject!=="nucbox-bridge")) return reply(401,{status:"unauthorized"});
      // Reuse existing durable attempt budgets, not a fresh quota per route.
      if(await limiter(identity,op)!==true) return reply(429,{status:"rate_limited"},60);
      const parsed=await boundedJson(request,max);
      if(parsed.error) return reply(parsed.error,{status:"invalid"});
      const b=parsed.value;
      if(op==="submit") {
        if(!validateSuggestion(b) || !ascii(b.text)) return reply(400,{status:"invalid"});
        const row=await repository.submit(identity.subject,b);
        if(row?.status==="accepted") {
          if(!isId(row.suggestion_id) || typeof row.replayed!=="boolean") throw new Error("invalid receipt");
          return reply(202,{status:"accepted",id:row.suggestion_id,replayed:row.replayed});
        }
        if(!row || !Object.hasOwn(codes,row.status)) throw new Error("invalid receipt");
        return reply(codes[row.status],{status:row.status},codes[row.status]===429?3600:undefined);
      }
      if(op==="claim") {
        if(!exact(b,[])) return reply(400,{status:"invalid"});
        const row=await repository.claim();
        if(row===null) return reply(200,{status:"empty"});
        const claim={id:row.suggestion_id,owner:row.owner_id,key:row.request_key,
          fence:row.fence,text:row.body,expiresAt:epoch(row.expires_at),leaseUntil:epoch(row.lease_until)};
        if(!validateClaim(claim,now()) || !ascii(claim.text)) throw new Error("invalid claim");
        return reply(200,claim);
      }
      if(!exact(b,["id","fence"]) || ![b.id,b.fence].every(isId))
        return reply(400,{status:"invalid"});
      const row=await repository.ack(b);
      if(typeof row?.ok!=="boolean") throw new Error("invalid ack");
      return reply(row.ok?200:409,{status:row.ok?"ok":"conflict"});
    } catch {
      console.error("Community gateway failed closed");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
