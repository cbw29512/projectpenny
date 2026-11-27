// Candidate production composition, not a deployed function.
import {createScopedQuery} from "./scoped-query.mjs";
import {runtimeFingerprint} from "./config-pin.mjs";
import {projectionConfig} from "./projection-config.mjs";
import {createWorkshopHandler} from "../projection/workshop-handler.mjs";
import {createWorkshopVerifier,unavailable} from "../projection/workshop-state.mjs";
import {createWorkshopRepository} from "../projection/workshop-repository.mjs";
import {reply} from "../gateway/response.mjs";

export function workshopConfig(env){return projectionConfig(env,"workshop");}

export function createWorkshopRuntime({env,Pool,allow}){
  let handler,pinned;
  return async request=>{
    try{
      const config=workshopConfig(env);
      if(config===null)return reply(503,unavailable(),60);
      const digest=runtimeFingerprint(config);
      if(handler&&pinned!==digest)throw Error("Workshop configuration changed");
      if(!handler){
        // The provider's request/credit limiter must be supplied explicitly.
        if(typeof Pool!=="function"||typeof allow!=="function")throw Error("Workshop dependencies unavailable");
        const query=scope=>{
          const pool=new Pool({connectionString:config.urls[scope],ssl:{rejectUnauthorized:true},
            max:1,connectionTimeoutMillis:5000,idleTimeoutMillis:5000,
            statement_timeout:5000,query_timeout:6000});
          pool.on("error",()=>console.error("Workshop projection pool unavailable"));
          return createScopedQuery(pool,config.roles[scope]);
        };
        handler=createWorkshopHandler({enabled:true,origin:config.origin,
          verify:createWorkshopVerifier(config.key),allow,
          repository:createWorkshopRepository({writerQuery:query("writer"),readerQuery:query("reader")})});
        pinned=digest;
      }
      return await handler(request);
    }catch{
      console.error("Workshop runtime unavailable.");
      return reply(503,unavailable(),60);
    }
  };
}
