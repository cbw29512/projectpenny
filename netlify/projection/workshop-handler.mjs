// Candidate only. No deployed endpoint or automatic provider provisioning.
import {boundedJson} from "../gateway/body.mjs";
import {reply} from "../gateway/response.mjs";
import {valid,browserView,unavailable} from "./workshop-state.mjs";
export function createWorkshopHandler({enabled=false,origin,verify,allow,repository,
    now=()=>Math.floor(Date.now()/1000)}){
  if(typeof origin!=="string"||!origin.startsWith("https://")||new URL(origin).origin!==origin
    ||typeof verify!=="function"||typeof allow!=="function"
    ||typeof repository?.publish!=="function"||typeof repository?.read!=="function")
    throw Error("Workshop dependencies incomplete");
  return async request=>{
    try{
      if(enabled!==true)return reply(503,unavailable(),60);
      const url=new URL(request.url);
      if(url.origin!==origin||url.search)return reply(400,{status:"invalid"});
      const source=request.headers.get("origin");
      if(source!==null&&source!==origin)return reply(403,{status:"denied"});
      const write=request.method==="POST"&&url.pathname==="/api/v1/bridge/workshop";
      const read=request.method==="GET"&&url.pathname==="/api/v1/workshop";
      if(!write&&!read)return reply(404,{status:"not_found"});
      if(write){
        const body=await boundedJson(request,256);
        if(body.error)return reply(body.error,{status:"invalid"});
        const observed=now();
        if(!valid(body.value,observed,15)||!verify(request.headers.get("authorization"),body.value,observed))
          return reply(401,{status:"unauthorized"});
        if(await allow("write",request)!==true)return reply(429,{status:"rate_limited"},60);
        const ok=await repository.publish(body.value);
        if(typeof ok!=="boolean")throw Error("invalid publication result");
        return reply(ok?200:409,{status:ok?"ok":"conflict"});
      }
      if(request.body!==null||request.headers.has("authorization"))return reply(400,{status:"invalid"});
      if(await allow("read",request)!==true)return reply(429,{status:"rate_limited"},60);
      return reply(200,browserView(await repository.read(),now()));
    }catch{
      console.error("Workshop endpoint unavailable.");
      return reply(503,unavailable(),60);
    }
  };
}
