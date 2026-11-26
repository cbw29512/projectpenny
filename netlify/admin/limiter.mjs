// Persistent admin attempt budget using the independently scoped DB connection.
import {isId} from "../gateway/state.mjs";
export function createAdminLimiter(adminQuery) {
  if(typeof adminQuery!=="function") throw new TypeError("admin query adapter required");
  return async (subject,op)=>{
    if(!isId(subject) || !["status","pause"].includes(op)) return false;
    try {
      const rows=await adminQuery("SELECT penny_mailbox.mailbox_admin_allow($1::uuid,$2::text) AS ok",[subject,op]);
      if(!Array.isArray(rows)||rows.length!==1||typeof rows[0]?.ok!=="boolean")
        throw new Error("invalid admin budget response");
      return rows[0].ok;
    } catch(e) {
      console.error("Admin rate limiter unavailable");
      throw e;
    }
  };
}
