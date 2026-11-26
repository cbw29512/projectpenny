import {runtimeFingerprint} from "./config-pin.mjs";
// Candidate only: provider-specific verified MFA adapter must be supplied.
import {loadAdminRuntime} from "./admin-config.mjs";
import {createScopedQuery} from "./scoped-query.mjs";
import {createAdminGateway} from "../admin/handler.mjs";
import {createAdminRepository} from "../admin/repository.mjs";
import {createAdminLimiter} from "../admin/limiter.mjs";
import {reply} from "../gateway/response.mjs";

export function createAdminRuntime({env,Pool,verifyAdmin,now}) {
  let handler, pinnedConfig;
  return async request=>{
    try {
      // Recheck the opt-in on every request, including warm instances.
      const c=loadAdminRuntime(env);
      if(c===null) return reply(503,{status:"paused"},60);
      const fingerprint=runtimeFingerprint(c);
      if(handler && fingerprint!==pinnedConfig) throw new Error("runtime configuration changed");
      if(typeof Pool!=="function" || typeof verifyAdmin!=="function")
        throw new Error("admin dependencies unavailable");
      if(!handler) {
        const pool=new Pool({connectionString:c.url,ssl:{rejectUnauthorized:true},
          max:1,connectionTimeoutMillis:5000,idleTimeoutMillis:5000,
          statement_timeout:5000,query_timeout:6000});
        pool.on("error",()=>console.error("Admin pool idle connection failed"));
        const query=createScopedQuery(pool,c.role);
        handler=createAdminGateway({origin:c.origin,enabled:true,verifyAdmin,now,
          repository:createAdminRepository(query),limiter:createAdminLimiter(query)});
        pinnedConfig=fingerprint;
      }
      return await handler(request);
    } catch {
      console.error("Admin runtime unavailable");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
