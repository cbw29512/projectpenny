// Durable DB-backed attempt limiter; no process-local counters.
import {isId} from "./state.mjs";
const memberOps=new Set(["submit","read"]);
const bridgeOps=new Set(["claim","ack","answer","reject"]);

export function createLimiter({memberQuery,bridgeQuery}) {
  if(typeof memberQuery!=="function" || typeof bridgeQuery!=="function")
    throw new TypeError("two scoped throttle adapters required");
  return async (identity,op)=>{
    try {
      let rows;
      if(identity?.scope==="member" && isId(identity.subject) && memberOps.has(op))
        rows=await memberQuery("SELECT penny_mailbox.mailbox_allow_member($1::uuid,$2::text) AS ok",
          [identity.subject,op]);
      else if(identity?.scope==="bridge" && identity.subject==="nucbox-bridge" && bridgeOps.has(op))
        rows=await bridgeQuery("SELECT penny_mailbox.mailbox_allow_bridge($1::text) AS ok",[op]);
      else return false;
      if(!Array.isArray(rows) || rows.length!==1 || typeof rows[0]?.ok!=="boolean")
        throw new Error("invalid throttle result");
      return rows[0].ok;
    } catch(e) {
      // Do not accept a request when shared counters are unavailable.
      console.error("Gateway throttle unavailable");
      throw e;
    }
  };
}
