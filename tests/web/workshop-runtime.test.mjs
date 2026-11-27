import test from "node:test";
import assert from "node:assert/strict";
import {createHmac} from "node:crypto";
import {workshopConfig,createWorkshopRuntime} from "../../netlify/runtime/workshop.mjs";
const origin="https://fixture.netlify.app",key="ab".repeat(32);
const env={CONTEXT:"production",PENNY_WORKSHOP_ENABLED:"true",PENNY_ORIGIN:origin,
  PENNY_PROJECTION_WRITER_DB_ROLE:"projection_writer",PENNY_PROJECTION_READER_DB_ROLE:"projection_reader",
  PENNY_PROJECTION_WRITER_DB_URL:"postgres://projection_writer:synthetic@db.example/penny",
  PENNY_PROJECTION_READER_DB_URL:"postgres://projection_reader:synthetic@db.example/penny",
  PENNY_WORKSHOP_KEY_HEX:key,PENNY_PROJECTION_KEY_HEX:"cd".repeat(32)};
const read=()=>new Request(origin+"/api/v1/workshop");
function write(){
  const now=Math.floor(Date.now()/1000);
  const value={sampled_at:now,stage:"prototype_reviewed",generated_at:now-2,expires_at:now+100};
  const mac=createHmac("sha256",Buffer.from(key,"hex")).update("penny-workshop-publish-v1."+
    [value.sampled_at,value.stage,value.generated_at,value.expires_at].join(".")).digest("hex");
  return new Request(origin+"/api/v1/bridge/workshop",{method:"POST",
    headers:{Authorization:"PennyWorkshop v1."+mac,"Content-Type":"application/json"},
    body:JSON.stringify(value)});
}
test("Workshop disabled outside production and requires provider limiter",async()=>{
  let pools=0;class Pool{constructor(){pools++;}}
  for(const e of [{},{...env,CONTEXT:"deploy-preview"},{...env,PENNY_WORKSHOP_ENABLED:"false"}])
    assert.equal((await createWorkshopRuntime({env:e,Pool,allow:async()=>true})(read())).status,503);
  assert.equal((await createWorkshopRuntime({env,Pool})(read())).status,503);
  assert.equal(pools,0);
});
test("reject wrong destination, shared credentials and TLS override",()=>{
  for(const e of [{...env,PENNY_ORIGIN:"https://penny.example"},
    {...env,PENNY_WORKSHOP_KEY_HEX:env.PENNY_PROJECTION_KEY_HEX},
    {...env,PENNY_MEMBER_KEY_HEX:key},
    {...env,PENNY_PROJECTION_WRITER_DB_ROLE:"projection_reader"},
    {...env,PENNY_PROJECTION_READER_DB_URL:env.PENNY_PROJECTION_READER_DB_URL+"?sslmode=disable"}])
    assert.throws(()=>workshopConfig(e));
});
test("runtime authenticates signed write and reads only via restricted role",async()=>{
  const calls=[],pools=[];let observation;
  class Pool{
    constructor(options){this.options=options;pools.push(this);}
    on(){}
    async connect(){
      const role=new URL(this.options.connectionString).username;
      return {release(){},query:async(s,a)=>{
        calls.push({role,s,a});
        if(s.includes("current_user"))return {rows:[{role,login:role,unsafe:false}]};
        if(s.includes("workshop_allow_write")&&role==="projection_writer")return {rows:[{ok:true}]};
        if(s.includes("workshop_allow_read")&&role==="projection_reader")return {rows:[{ok:true}]};
        if(s.includes("workshop_publish")&&role==="projection_writer"){
          const [sampled_at,stage,generated_at,expires_at]=a;
          observation={sampled_at,stage,generated_at,expires_at};return {rows:[{ok:true}]};
        }
        if(s.includes("workshop_read")&&role==="projection_reader")return {rows:observation?[observation]:[]};
        throw Error("unexpected query");
      }};
    }
  }
  const e={...env},handler=createWorkshopRuntime({env:e,Pool,allow:async()=>true});
  assert.equal((await handler(write())).status,200);
  const response=await handler(read());
  assert.equal(response.status,200);
  assert.equal((await response.json()).stage,"prototype_reviewed");
  assert.equal(pools.length,2);assert.ok(pools.every(p=>p.options.ssl.rejectUnauthorized));
  assert.equal(calls.length,8);
  assert.deepEqual(calls.map(c=>c.role),["projection_writer","projection_writer","projection_writer","projection_writer","projection_reader","projection_reader","projection_reader","projection_reader"]);
  e.PENNY_WORKSHOP_ENABLED="false";
  assert.equal((await handler(read())).status,503);
  e.PENNY_WORKSHOP_ENABLED="true";e.PENNY_WORKSHOP_KEY_HEX="ef".repeat(32);
  assert.equal((await handler(read())).status,503);
  assert.equal(calls.length,8);
});
