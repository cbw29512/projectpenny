// Dedicated admin connection; never use member, bridge or database owner.
export function createAdminRepository(adminQuery) {
  if(typeof adminQuery!=="function") throw new TypeError("admin connection required");
  async function one(statement,args) {
    try {
      const rows=await adminQuery(statement,args);
      if(!Array.isArray(rows)||rows.length>1) throw new Error("unexpected admin result");
      return rows[0]??null;
    } catch(e) {
      console.error("Admin database operation failed");
      throw e;
    }
  }
  return Object.freeze({
    status:async id=>{
      const row=await one("SELECT * FROM penny_mailbox.mailbox_admin_status($1::uuid)",[id]);
      if(row===null) return null;
      // PostgreSQL drivers may represent bigint counts as decimal strings.
      const count=v=>typeof v==="string" && /^[0-9]{1,3}$/.test(v)?Number(v):v;
      return {admission_open:row.admission_open,pending:count(row.pending),processing:count(row.processing)};
    },
    pause:async id=>(await one("SELECT penny_mailbox.mailbox_admin_pause($1::uuid) AS ok",[id]))?.ok,
  });
}
