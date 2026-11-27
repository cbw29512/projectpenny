// No production runtime, credentials, database, or user input.
// Bind draft and production smoke URLs to this project's trusted site ID.
import {reply} from "../gateway/response.mjs";
const SITE="28c495fc-f47a-427b-9ee2-95d4eadd2d8d";
const DEPLOY=/^[a-f0-9]{24}$/;
const routes={read:["GET","/api/v1/workshop"],write:["POST","/api/v1/bridge/workshop"]};

export function smoke(operation){
  if(!Object.hasOwn(routes,operation))throw Error("unknown smoke route");
  return (request,context)=>{
    try{
      const url=new URL(request.url),id=context?.deploy?.id;
      const validHost=url.hostname==="projectpenny.netlify.app"||
        (typeof id==="string"&&DEPLOY.test(id)&&url.hostname===id+"--projectpenny.netlify.app");
      const [method,path]=routes[operation];
      if(context?.site?.id!==SITE||!validHost||url.protocol!=="https:"||
          url.port||url.search||url.pathname!==path||request.method!==method)
        return reply(404,{status:"not_found"});
      // Fixed marker distinguishes the staged function from generic platform errors.
      return reply(503,{schema:"penny-workshop-smoke-v1",status:"unavailable",operation},60);
    }catch{
      console.error("Workshop smoke route unavailable.");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
