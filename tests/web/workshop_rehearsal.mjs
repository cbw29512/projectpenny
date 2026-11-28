// Test-only subprocess transport. No HTTP listener, real host or provider key.
import {spawnSync} from "node:child_process";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {createWorkshopHandler} from "../../netlify/projection/workshop-handler.mjs";
import {createWorkshopVerifier} from "../../netlify/projection/workshop-state.mjs";
import {createWorkshopRepository} from "../../netlify/projection/workshop-repository.mjs";
import {createWorkshopLimiter} from "../../netlify/projection/workshop-limiter.mjs";
import {createWorkshopReader} from "../../website/assets/workshop-reader.mjs";

const origin="https://fixture.netlify.app",key=Buffer.alloc(32,120);
const statements=new Map([
  ["SELECT penny_mailbox.workshop_allow_write() AS ok",["writer","allow_write"]],
  ["SELECT penny_mailbox.workshop_allow_read() AS ok",["reader","allow_read"]],
  ["SELECT penny_mailbox.workshop_publish($1::bigint,$2::text,$3::bigint,$4::bigint) AS ok",["writer","publish"]],
  ["SELECT * FROM penny_mailbox.workshop_read()",["reader","read"]],
]);
function query(scope){
  return async (statement,args)=>{
    const entry=statements.get(statement);
    if(!entry||entry[0]!==scope)throw Error("unexpected fixture statement");
    const result=spawnSync(process.env.PENNY_REHEARSAL_PYTHON,
      [fileURLToPath(new URL("./workshop_rehearsal_sql.py",import.meta.url))],
      {input:JSON.stringify({operation:entry[1],args}),encoding:"utf8",timeout:5000,maxBuffer:16384});
    if(result.status!==0||result.error)throw Error("disposable SQL query failed");
    return JSON.parse(result.stdout);
  };
}
try{
  const input=JSON.parse(readFileSync(0,"utf8"));
  const queries={writerQuery:query("writer"),readerQuery:query("reader")};
  const handler=createWorkshopHandler({enabled:true,origin,verify:createWorkshopVerifier(key),
    allow:createWorkshopLimiter({edgeAllow:async()=>true,...queries}),
    repository:createWorkshopRepository(queries)});
  if(input.action==="browser"){
    let response;
    const reader=createWorkshopReader({enabled:true,clock:Date.now,fetcher:async(path,options)=>{
      const result=await handler(new Request(origin+path,options));
      response={status:result.status,body:await result.clone().json()};
      return result;
    }});
    await reader.read();
    process.stdout.write(JSON.stringify({...response,state:reader.snapshot().state}));
    reader.close();
  }else if(input.action==="post"){
    const response=await handler(new Request(origin+input.path,{method:"POST",
      headers:input.headers,body:input.body}));
    process.stdout.write(JSON.stringify({status:response.status,
      headers:Object.fromEntries(response.headers),body:await response.text()}));
  }else throw Error("unknown fixture action");
}catch(e){
  console.error("Workshop rehearsal runner failed:",e.name);
  process.exitCode=1;
}
