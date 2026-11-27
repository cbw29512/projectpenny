// Not a deployed function. Production composition with explicit isolated credentials.
import {createScopedQuery} from "./scoped-query.mjs";
import {runtimeFingerprint} from "./config-pin.mjs";
import {createActivityHandler} from "../projection/handler.mjs";
import {createActivityVerifier} from "../projection/state.mjs";
import {createActivityRepository} from "../projection/repository.mjs";
import {reply} from "../gateway/response.mjs";
const ROLE=/^[a-z][a-z0-9_]{0,62}$/;
export function activityConfig(env){
  if(env.CONTEXT!=="production"||env.PENNY_ACTIVITY_ENABLED!=="true")return null;
  const origin=env.PENNY_ORIGIN;
  if(typeof origin!=="string"||!origin.startsWith("https://")||new URL(origin).origin!==origin)
    throw Error("invalid activity origin");
  const roles={writer:env.PENNY_PROJECTION_WRITER_DB_ROLE,reader:env.PENNY_PROJECTION_READER_DB_ROLE};
  const urls={writer:env.PENNY_PROJECTION_WRITER_DB_URL,reader:env.PENNY_PROJECTION_READER_DB_URL};
  const other=[env.PENNY_MEMBER_DB_ROLE,env.PENNY_BRIDGE_DB_ROLE,env.PENNY_ADMIN_DB_ROLE];
  if(!Object.values(roles).every(x=>typeof x==="string"&&ROLE.test(x)&&!other.includes(x))
      ||roles.writer===roles.reader)throw Error("isolated projection roles required");
  for(const name of ["writer","reader"]){
    const url=new URL(urls[name]);
    if(!["postgres:","postgresql:"].includes(url.protocol)||url.search||url.hash||!url.hostname
        ||!url.password||decodeURIComponent(url.username)!==roles[name]||url.pathname.length<2)
      throw Error("invalid projection connection");
  }
  const key=env.PENNY_PROJECTION_KEY_HEX;
  if(typeof key!=="string"||! /^[a-f0-9]{64,128}$/.test(key)||key.length%2
     ||[env.PENNY_MEMBER_KEY_HEX,env.PENNY_BRIDGE_KEY_HEX].some(x=>typeof x==="string"&&x.toLowerCase()===key))
    throw Error("separate projection key required");
  return {origin,roles,urls,key:Buffer.from(key,"hex")};
}
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
