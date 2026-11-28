// Synthetic conversation transport: real browser state, HTTP gateway and SQL scopes.
import {spawnSync} from "node:child_process";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {createHmac} from "node:crypto";
import {createGateway} from "../../netlify/gateway/handler.mjs";
import {createVerifier} from "../../netlify/gateway/auth.mjs";
import {createLimiter} from "../../netlify/gateway/limiter.mjs";
import {createRepository} from "../../netlify/gateway/repository.mjs";
import {createBetaMailbox} from "../../website/assets/beta-mailbox.mjs";
const origin="https://fixture.netlify.app",memberKey=Buffer.alloc(32,109),bridgeKey=Buffer.alloc(32,98);
const statements=new Map([
  ["SELECT penny_mailbox.mailbox_allow_member($1::uuid,$2::text) AS ok",["member","member_limit"]],
  ["SELECT penny_mailbox.mailbox_allow_bridge($1::text) AS ok",["bridge","bridge_limit"]],
  ["SELECT * FROM penny_mailbox.mailbox_submit($1::uuid,$2::uuid,$3::text)",["member","submit"]],
  ["SELECT * FROM penny_mailbox.mailbox_read($1::uuid,$2::uuid)",["member","mailbox_read"]],
  ["SELECT * FROM penny_mailbox.mailbox_claim()",["bridge","claim"]],
  ["SELECT penny_mailbox.mailbox_ack($1::uuid,$2::uuid,$3::uuid) AS ok",["bridge","ack"]],
  ["SELECT penny_mailbox.mailbox_answer($1::uuid,$2::uuid,$3::text) AS ok",["bridge","answer"]],
  ["SELECT penny_mailbox.mailbox_reject($1::uuid,$2::uuid) AS ok",["bridge","reject"]],
]);
function query(scope){
  return async(statement,args)=>{
    const entry=statements.get(statement);
    if(!entry||entry[0]!==scope)throw Error("unexpected fixture statement");
    const result=spawnSync(process.env.PENNY_REHEARSAL_PYTHON,
      [fileURLToPath(new URL("./workshop_rehearsal_sql.py",import.meta.url))],
      {input:JSON.stringify({operation:entry[1],args}),encoding:"utf8",timeout:5000,maxBuffer:100000});
    if(result.status!==0||result.error)throw Error("disposable SQL failed");
    return JSON.parse(result.stdout);
  };
}
function token(owner){
  const now=Math.floor(Date.now()/1000);
  const payload=Buffer.from(JSON.stringify({aud:"member",sub:owner,iat:now,exp:now+300})).toString("base64url");
  return "v1."+payload+"."+createHmac("sha256",memberKey).update("penny-beta-v1."+payload).digest("base64url");
}
try{
  const input=JSON.parse(readFileSync(0,"utf8"));
  const queries={memberQuery:query("member"),bridgeQuery:query("bridge")};
  const handler=createGateway({origin,enabled:true,verify:createVerifier({memberKey,bridgeKey}),
    limiter:createLimiter(queries),repository:createRepository(queries)});
  if(input.action==="browser"){
    let now=Date.now();
    const mailbox=createBetaMailbox({enabled:true,uuid:()=>input.key,clock:()=>now,
      fetcher:(path,opts)=>handler(new Request(origin+path,opts))});
    if(!mailbox.signIn(token(input.owner)))throw Error("fixture signin refused");
    const submitted=await mailbox.submit(input.question);
    now+=15000;
    const observed=input.read?await mailbox.read():submitted;
    mailbox.signOut();
    process.stdout.write(JSON.stringify({submitted,observed,cleared:mailbox.snapshot()}));
  }else{
    const request=input.action==="foreign"
      ?new Request(origin+"/api/v1/questions/"+input.id,{headers:{Authorization:"Bearer "+token(input.owner)}})
      :new Request(origin+input.path,{method:"POST",headers:input.headers,body:input.body});
    const response=await handler(request);
    process.stdout.write(JSON.stringify({status:response.status,
      headers:Object.fromEntries(response.headers),body:await response.text()}));
  }
}catch(e){
  console.error("Conversation rehearsal failed:",e.name);process.exitCode=1;
}
