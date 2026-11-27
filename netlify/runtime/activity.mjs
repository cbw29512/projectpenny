// Not a deployed function. Production composition with explicit isolated credentials.
import {createScopedQuery} from "./scoped-query.mjs";
import {runtimeFingerprint} from "./config-pin.mjs";
import {createActivityHandler} from "../projection/handler.mjs";
import {createActivityVerifier} from "../projection/state.mjs";
import {createActivityRepository} from "../projection/repository.mjs";
import {reply} from "../gateway/response.mjs";
import {projectionConfig} from "./projection-config.mjs";
export function activityConfig(env){return projectionConfig(env,"activity");}
export function createActivityRuntime({env,Pool,allow}){
  let handler,pinned;
  return async request=>{
    try{
      const config=activityConfig(env);
      if(config===null)return reply(503,{status:"paused"},60);
      const digest=runtimeFingerprint(config);
      if(handler&&pinned!==digest)throw Error("projection configuration changed");
      if(!handler){
        if(typeof Pool!=="function"||typeof allow!=="function")throw Error("projection adapter unavailable");
        const query=scope=>{
          const pool=new Pool({connectionString:config.urls[scope],ssl:{rejectUnauthorized:true},
            max:1,connectionTimeoutMillis:5000,idleTimeoutMillis:5000,statement_timeout:5000,query_timeout:6000});
          pool.on("error",()=>console.error("Projection pool unavailable"));
          return createScopedQuery(pool,config.roles[scope]);
        };
        handler=createActivityHandler({enabled:true,origin:config.origin,
          verify:createActivityVerifier(config.key),allow,
          repository:createActivityRepository({writerQuery:query("writer"),readerQuery:query("reader")})});
        pinned=digest;
      }
      return await handler(request);
    }catch{
      console.error("Activity runtime unavailable.");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
