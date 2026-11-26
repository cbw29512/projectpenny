import {route,validateBody} from "./state.mjs";
import {boundedJson} from "./body.mjs";
import {reply,resultResponse} from "./response.mjs";

// Testable HTTP core only. Fail closed without a real admission limiter.
// A distributed limiter must precede storage; this is not a DDoS shield.
export function createGateway({verify,limiter,repository,origin,enabled=false}) {
  if(typeof verify!=="function" || typeof limiter!=="function" ||
     typeof origin!=="string" || new URL(origin).origin!==origin ||
     !origin.startsWith("https://") || !repository ||
     !["submit","read","claim","ack","answer","reject"].every(k=>typeof repository[k]==="function"))
    throw new TypeError("gateway dependencies incomplete");
  return async request=>{
    try {
      if(enabled!==true) return reply(503,{status:"paused"},60);
      const url=new URL(request.url);
      if(url.origin!==origin || url.search) return reply(400,{status:"invalid"});
      const spec=route(request.method,url.pathname);
      if(!spec) return reply(404,{status:"not_found"});
      const source=request.headers.get("origin");
      if(source!==null && source!==origin) return reply(403,{status:"denied"});
      const identity=verify(request.headers.get("authorization"),spec.scope);
      if(!identity || identity.scope!==spec.scope) return reply(401,{status:"unauthorized"});
      // Limiter is mandatory and must explicitly allow this subject/action.
      // Its backend must not trust a client-supplied IP or tier.
      if(await limiter(identity,spec.op)!==true) return reply(429,{status:"rate_limited"},60);
      let body;
      if(spec.max) {
        const parsed=await boundedJson(request,spec.max);
        if(parsed.error) return reply(parsed.error,{status:"invalid"});
        body=parsed.value;
        if(!validateBody(spec.op,body)) return reply(400,{status:"invalid"});
      } else if(request.body!==null) return reply(400,{status:"invalid"});
      let row;
      if(spec.op==="submit") row=await repository.submit(identity.subject,body);
      else if(spec.op==="read") row=await repository.read(identity.subject,spec.id);
      else if(spec.op==="claim") row=await repository.claim();
      else row=await repository[spec.op](body);
      return resultResponse(spec.op,row);
    } catch {
      console.error("Gateway request failed closed");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
