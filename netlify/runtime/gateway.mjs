// Candidate function composition; not in the deployed functions directory.
import {loadRuntime} from "./config.mjs";
import {createScopedQuery} from "./scoped-query.mjs";
import {createGateway} from "../gateway/handler.mjs";
import {createVerifier} from "../gateway/auth.mjs";
import {createRepository} from "../gateway/repository.mjs";
import {createLimiter} from "../gateway/limiter.mjs";
import {reply} from "../gateway/response.mjs";

export function createRuntimeHandler({env,Pool}) {
  let handler;
  return async request=>{
    try {
      if(!handler) {
        const c=loadRuntime(env);
        if(c===null) return reply(503,{status:"paused"},60);
        if(typeof Pool!=="function") throw new Error("database driver unavailable");
        const options=scope=>({connectionString:c.urls[scope],
          ssl:{rejectUnauthorized:true},max:1,
          connectionTimeoutMillis:5000,idleTimeoutMillis:5000,
          statement_timeout:5000,query_timeout:6000});
        const member=new Pool(options("member")),bridge=new Pool(options("bridge"));
        for(const pool of [member,bridge])
          pool.on("error",()=>console.error("Scoped pool idle connection failed"));
        const queries={memberQuery:createScopedQuery(member,c.roles.member),
          bridgeQuery:createScopedQuery(bridge,c.roles.bridge)};
        handler=createGateway({origin:c.origin,enabled:true,
          verify:createVerifier(c),repository:createRepository(queries),
          limiter:createLimiter(queries)});
      }
      return await handler(request);
    } catch {
      console.error("Private beta runtime unavailable");
      return reply(503,{status:"unavailable"},60);
    }
  };
}
