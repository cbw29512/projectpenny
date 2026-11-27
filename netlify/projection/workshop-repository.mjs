// Fixed scoped queries only; never query the local private database.
function clock(raw){
  if(typeof raw!=="number"&&(typeof raw!=="string"||!/^\d{1,16}$/.test(raw)))
    throw Error("invalid clock");
  const n=Number(raw);
  if(!Number.isSafeInteger(n)||n<0)throw Error("invalid clock");
  return n;
}
export function createWorkshopRepository({writerQuery,readerQuery}){
  if(typeof writerQuery!=="function"||typeof readerQuery!=="function")throw Error("isolated queries required");
  return Object.freeze({
    async publish(value){
      const rows=await writerQuery("SELECT penny_mailbox.workshop_publish($1::bigint,$2::text,$3::bigint,$4::bigint) AS ok",
        [value.sampled_at,value.stage,value.generated_at,value.expires_at]);
      if(!Array.isArray(rows)||rows.length!==1||typeof rows[0].ok!=="boolean")throw Error("invalid write");
      return rows[0].ok;
    },
    async read(){
      const rows=await readerQuery("SELECT * FROM penny_mailbox.workshop_read()",[]);
      if(!Array.isArray(rows)||rows.length>1)throw Error("invalid read");
      if(!rows.length)return null;
      const row=rows[0];
      return {sampled_at:clock(row.sampled_at),stage:row.stage,
        generated_at:clock(row.generated_at),expires_at:clock(row.expires_at)};
    }
  });
}
