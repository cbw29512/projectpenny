// Provider edge admission must happen first; database budget is defense in depth.
export function createWorkshopLimiter({edgeAllow,writerQuery,readerQuery}){
  if([edgeAllow,writerQuery,readerQuery].some(fn=>typeof fn!=="function"))
    throw Error("Workshop admission dependencies missing");
  return async (op,request)=>{
    try{
      if(op!=="read"&&op!=="write")return false;
      if(await edgeAllow(op,request)!==true)return false;
      const rows=op==="read"
        ?await readerQuery("SELECT penny_mailbox.workshop_allow_read() AS ok",[])
        :await writerQuery("SELECT penny_mailbox.workshop_allow_write() AS ok",[]);
      if(!Array.isArray(rows)||rows.length!==1||typeof rows[0]?.ok!=="boolean")
        throw Error("invalid Workshop budget result");
      return rows[0].ok;
    }catch(e){
      console.error("Workshop admission unavailable.");
      throw e;
    }
  };
}
