// Candidate handlers: provider edge/credit gate must be installed before activation.
import {boundedJson} from "../gateway/body.mjs";
import {reply} from "../gateway/response.mjs";
import {sampleValid} from "./state.mjs";

export function createActivityHandler({enabled=false,origin,verify,allow,repository,
    now=()=>Math.floor(Date.now()/1000)}){
  if(typeof origin!=="string"||!origin.startsWith("https://")||new URL(origin).origin!==origin
    ||typeof verify!=="function"||typeof allow!=="function"
    ||typeof repository?.publish!=="function"||typeof repository?.read!=="function")
    throw Error("projection dependencies incomplete");
  return async request=>{
    try{
      if(enabled!==true)return reply(503,{status:"paused"},60);
      const url=new URL(request.url);
      if(url.origin!==origin||url.search)return reply(400,{status:"invalid"});
      const source=request.headers.get("origin");
      if(source!==null&&source!==origin)return reply(403,{status:"denied"});
      const write=request.method==="POST"&&url.pathname==="/api/v1/bridge/activity";
      const read=request.method==="GET"&&url.pathname==="/api/v1/activity";
      if(!write&&!read)return reply(404,{status:"not_found"});
      if(write){
        const body=await boundedJson(request,256);
        if(body.error)return reply(body.error,{status:"invalid"});
        if(!verify(request.headers.get("authorization"),body.value,now()))
          return reply(401,{status:"unauthorized"});
        if(await allow("write",request)!==true)return reply(429,{status:"rate_limited"},60);
        const result=await repository.publish(body.value);
        if(typeof result!=="boolean")throw Error("invalid publish result");
        return reply(result?200:409,{status:result?"ok":"conflict"});
      }
      if(request.body!==null||request.headers.has("authorization"))
        return reply(400,{status:"invalid"});
      if(await allow("read",request)!==true)return reply(429,{status:"rate_limited"},60);
      const value=await repository.read();
      if(value===null)return reply(200,{status:"unavailable"});
      if(!sampleValid(value,now(),120))return reply(200,{status:"unavailable"});
      // No private rows, no inference. No cache until provider edge policy is certified.
      return reply(200,{sampled_at:value.sampled_at,activity:value.activity});
    }catch{
      console.error("Activity endpoint unavailable.");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
