// Trusted platform context, not client-supplied headers. Keep the smoke
// endpoints dependency-free until the real provider deployment is reviewed.
import {reply} from "../gateway/response.mjs";
import {unavailable} from "../projection/workshop-state.mjs";
const SITE_ID="28c495fc-f47a-427b-9ee2-95d4eadd2d8d";
const ORIGIN="https://projectpenny.netlify.app";
const ROUTES=Object.freeze({read:{path:"/api/v1/workshop",method:"GET"},
  write:{path:"/api/v1/bridge/workshop",method:"POST"}});

export function createWorkshopEntry({operation,env,loadRuntime}){
  if(!Object.hasOwn(ROUTES,operation)||typeof loadRuntime!=="function")
    throw Error("invalid Workshop entry");
  let runtime;
  return async (request,context)=>{
    try{
      const route=ROUTES[operation],url=new URL(request.url);
      if(url.origin!==ORIGIN||url.pathname!==route.path||url.search||request.method!==route.method)
        return reply(404,{status:"not_found"});
      // Only the actual published production deploy of our identified site.
      if(context?.site?.id!==SITE_ID||context?.deploy?.context!=="production"
          ||context.deploy.published!==true||env.PENNY_ORIGIN!==ORIGIN
          ||env.PENNY_WORKSHOP_ENABLED!=="true"
          ||typeof context.deploy.id!=="string"||!context.deploy.id
          ||env.PENNY_WORKSHOP_REVIEWED_DEPLOY_ID!==context.deploy.id)
        return reply(503,unavailable(),60);
      // The reviewed deploy ID is an operator attestation, not independent
      // proof of edge enforcement. Never let an old deploy silently activate.
      if(!runtime)runtime=await loadRuntime({...env,CONTEXT:context.deploy.context});
      if(typeof runtime!=="function")throw Error("runtime unavailable");
      return await runtime(request);
    }catch{
      console.error("Workshop entry unavailable.");
      return reply(503,unavailable(),60);
    }
  };
}
