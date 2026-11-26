// Validate the actual role on the same client used for the fixed query.
const CHECK=`SELECT current_user AS role,session_user AS login,
    r.rolsuper OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication OR r.rolbypassrls
      OR EXISTS(SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.member=r.oid)
      OR pg_catalog.has_schema_privilege(r.oid,'penny_mailbox','CREATE')
      OR EXISTS(SELECT 1 FROM pg_catalog.pg_namespace n
        WHERE n.nspname='penny_mailbox' AND n.nspowner=r.oid) AS unsafe
    FROM pg_catalog.pg_roles r WHERE r.rolname=current_user`;

export function createScopedQuery(pool,role) {
  if(typeof pool?.connect!=="function" || typeof role!=="string")
    throw new TypeError("scoped pool required");
  return async (statement,args)=>{
    let client,failed=false;
    try {
      client=await pool.connect();
      const check=await client.query(CHECK);
      const row=check.rows?.[0];
      if(check.rows?.length!==1 || row.role!==role || row.login!==role || row.unsafe!==false)
        throw new Error("unsafe database principal");
      const result=await client.query(statement,args);
      if(!Array.isArray(result.rows)) throw new Error("invalid query response");
      return result.rows;
    } catch(e) {
      failed=true;
      console.error("Scoped database operation refused");
      throw e;
    } finally {
      if(client) client.release(failed);
    }
  };
}
