// Adapter accepts independently scoped query functions (parameterized SQL).
// No driver, connection string or privileged role is chosen by a request.
export function createRepository({memberQuery,bridgeQuery}) {
  if(typeof memberQuery!=="function" || typeof bridgeQuery!=="function")
    throw new TypeError("two scoped query adapters required");
  async function rows(query,statement,args) {
    try {
      const result=await query(statement,args);
      if(!Array.isArray(result) || result.length>1) throw new Error("unexpected row count");
      return result;
    } catch(e) {
      // Sanitized boundary logging, no SQL parameters or connection strings.
      console.error("Mailbox operation failed");
      throw e;
    }
  }
  const one=async(q,s,a)=> (await rows(q,s,a))[0]??null;
  return Object.freeze({
    submit:(owner,b)=>one(memberQuery,"SELECT * FROM penny_mailbox.mailbox_submit($1::uuid,$2::uuid,$3::text)",[owner,b.key,b.text]),
    read:(owner,id)=>one(memberQuery,"SELECT * FROM penny_mailbox.mailbox_read($1::uuid,$2::uuid)",[owner,id]),
    claim:()=>one(bridgeQuery,"SELECT * FROM penny_mailbox.mailbox_claim()",[]),
    ack:(b)=>one(bridgeQuery,"SELECT penny_mailbox.mailbox_ack($1::uuid,$2::uuid,$3::uuid) AS ok",[b.id,b.fence,b.localTask]),
    answer:(b)=>one(bridgeQuery,"SELECT penny_mailbox.mailbox_answer($1::uuid,$2::uuid,$3::text) AS ok",[b.id,b.fence,b.text]),
    reject:(b)=>one(bridgeQuery,"SELECT penny_mailbox.mailbox_reject($1::uuid,$2::uuid) AS ok",[b.id,b.fence]),
  });
}
