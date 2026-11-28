// Separate candidate adapter: fixed queries, no request-selected role or SQL.
export function createCommunityRepository({memberQuery,bridgeQuery}) {
  if(typeof memberQuery!=="function" || typeof bridgeQuery!=="function")
    throw new TypeError("scoped community adapters required");
  async function one(query,statement,args) {
    try {
      const rows=await query(statement,args);
      if(!Array.isArray(rows) || rows.length>1) throw new Error("invalid row count");
      return rows[0]??null;
    } catch(error) {
      console.error("Community mailbox operation failed");
      throw error;
    }
  }
  return Object.freeze({
    submit:(owner,b)=>one(memberQuery,
      "SELECT * FROM penny_mailbox.community_mailbox_submit($1::uuid,$2::uuid,$3::text)",[owner,b.key,b.text]),
    claim:()=>one(bridgeQuery,
      "SELECT * FROM penny_mailbox.community_mailbox_claim()",[]),
    ack:b=>one(bridgeQuery,
      "SELECT penny_mailbox.community_mailbox_ack($1::uuid,$2::uuid) AS ok",[b.id,b.fence])
  });
}
