// Exact fixed routines, independently scoped adapters; no arbitrary queries.
export function createActivityRepository({writerQuery,readerQuery}){
  if(typeof writerQuery!=="function"||typeof readerQuery!=="function")
    throw Error("separate projection queries required");
  return Object.freeze({
    async publish(value){
      const rows=await writerQuery("SELECT penny_mailbox.activity_publish($1::bigint,$2::text) AS ok",
        [value.sampled_at,value.activity]);
      if(!Array.isArray(rows)||rows.length!==1||typeof rows[0].ok!=="boolean")
        throw Error("invalid projection write result");
      return rows[0].ok;
    },
    async read(){
      const rows=await readerQuery("SELECT * FROM penny_mailbox.activity_read()",[]);
      if(!Array.isArray(rows)||rows.length>1)throw Error("invalid projection read result");
      if(rows.length===0)return null;
      // pg returns bigint as a string by default; do not accept arbitrary coercion.
      const raw=rows[0].sampled_at;
      if(typeof raw!=="number"&&(typeof raw!=="string"||!/^\d{1,16}$/.test(raw)))
        throw Error("invalid observation clock");
      const sampled_at=Number(raw);
      if(!Number.isSafeInteger(sampled_at)||sampled_at<=0)throw Error("invalid observation clock");
      return {sampled_at,activity:rows[0].activity};
    }
  });
}
