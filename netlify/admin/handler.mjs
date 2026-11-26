// Separate, default-disabled administrative API core. No provider adapter yet.
import {isId,exact} from "../gateway/state.mjs";
import {boundedJson} from "../gateway/body.mjs";
import {reply} from "../gateway/response.mjs";

export function createAdminGateway({verifyAdmin,limiter,repository,origin,
    now=()=>Math.floor(Date.now()/1000),enabled=false}) {
  if(typeof verifyAdmin!=="function" || typeof limiter!=="function" ||
     typeof repository?.status!=="function" || typeof repository?.pause!=="function" ||
     typeof origin!=="string" || new URL(origin).origin!==origin || !origin.startsWith("https://"))
    throw new TypeError("admin dependencies incomplete");
  return async request=>{
    try {
      if(enabled!==true) return reply(503,{status:"paused"});
      const url=new URL(request.url);
      if(url.origin!==origin || url.search) return reply(400,{status:"invalid"});
      const read=request.method==="GET" && url.pathname==="/api/v1/admin/status";
      const pause=request.method==="POST" && url.pathname==="/api/v1/admin/pause-admission";
      if(!read && !pause) return reply(404,{status:"not_found"});
      const source=request.headers.get("origin");
      // Mutations require exact origin, no cross-origin or implicit cookie auth.
      if((pause && source!==origin) || (source!==null && source!==origin))
        return reply(403,{status:"denied"});
      const bearer=request.headers.get("authorization");
      if(!bearer || !bearer.startsWith("Bearer ") || bearer.length>8192)
        return reply(401,{status:"unauthorized"});
      // Trusted provider adapter must independently verify issuer, audience,
      // signature, session revocation, MFA evidence and admin identity.
      // No client-supplied role or MFA fields are accepted.
      const session=await verifyAdmin(bearer);
      const t=now();
      if(!exact(session,["scope","subject","mfaAt","expiresAt"]) ||
         session.scope!=="admin" || !isId(session.subject) ||
         !Number.isSafeInteger(t) || !Number.isSafeInteger(session.mfaAt) ||
         !Number.isSafeInteger(session.expiresAt) || session.mfaAt>t ||
         session.expiresAt<=t || session.expiresAt>t+900 ||
         t-session.mfaAt>(pause?300:900))
        return reply(401,{status:"unauthorized"});
      if(await limiter(session.subject,read?"status":"pause")!==true)
        return reply(429,{status:"rate_limited"},60);
      if(read) {
        if(request.body!==null) return reply(400,{status:"invalid"});
        const row=await repository.status(session.subject);
        if(row===null) return reply(403,{status:"denied"});
        if(typeof row?.admission_open!=="boolean" ||
           ![row.pending,row.processing].every(n=>Number.isSafeInteger(n)&&n>=0&&n<=512))
          throw new Error("invalid status");
        return reply(200,{admissionOpen:row.admission_open,pending:row.pending,processing:row.processing});
      }
      const body=await boundedJson(request,256);
      if(body.error) return reply(body.error,{status:"invalid"});
      if(!exact(body.value,["confirm"]) || body.value.confirm!=="PAUSE ADMISSION")
        return reply(400,{status:"invalid"});
      const ok=await repository.pause(session.subject);
      if(typeof ok!=="boolean") throw new Error("invalid pause result");
      return ok?reply(200,{status:"admission_closed"}):reply(403,{status:"denied"});
    } catch {
      console.error("Admin request failed closed");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
