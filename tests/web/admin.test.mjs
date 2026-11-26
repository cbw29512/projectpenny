import test from "node:test";
import assert from "node:assert/strict";
import {randomUUID} from "node:crypto";
import {createAdminGateway} from "../../netlify/admin/handler.mjs";
import {createAdminRepository} from "../../netlify/admin/repository.mjs";

const origin="https://penny.example",subject=randomUUID(),t=1000;
const session={scope:"admin",subject,mfaAt:t-60,expiresAt:t+600};
function fixture(overrides={}) {
  const calls=[];
  const handler=createAdminGateway({origin,enabled:true,now:()=>t,
    verifyAdmin:async()=>session,limiter:async()=>true,
    repository:{status:async id=>{calls.push(["status",id]);return {admission_open:true,pending:2,processing:1,secret:"hidden"};},
      pause:async id=>{calls.push(["pause",id]);return true;}},...overrides});
  return {handler,calls};
}
const status=()=>new Request(origin+"/api/v1/admin/status",{headers:{Authorization:"Bearer synthetic"}});
const pause=(body={confirm:"PAUSE ADMISSION"},source=origin)=>new Request(origin+"/api/v1/admin/pause-admission",{
  method:"POST",headers:{Authorization:"Bearer synthetic",Origin:source,"Content-Type":"application/json"},body:JSON.stringify(body)});
test("default closed; admin status is allowlisted and private",async()=>{
  const closed=fixture({enabled:undefined});
  assert.equal((await closed.handler(status())).status,503);
  const {handler,calls}=fixture();
  const result=await handler(status());
  assert.deepEqual(await result.json(),{admissionOpen:true,pending:2,processing:1});
  assert.equal(result.headers.get("cache-control"),"private, no-store");
  assert.deepEqual(calls,[["status",subject]]);
});
test("reject member, expired, absent, malformed or stale MFA",async()=>{
  for(const value of [null,{...session,scope:"member"},{...session,expiresAt:t},
    {...session,mfaAt:t-901},{...session,mfaAt:t+1},{...session,role:"admin"}]) {
    const {handler,calls}=fixture({verifyAdmin:async()=>value});
    assert.equal((await handler(status())).status,401);assert.deepEqual(calls,[]);
  }
});
test("pause requires recent MFA, origin and exact confirmation",async()=>{
  const stale=fixture({verifyAdmin:async()=>({...session,mfaAt:t-301})});
  assert.equal((await stale.handler(pause())).status,401);
  const {handler,calls}=fixture();
  assert.equal((await handler(pause(undefined,"https://other.example"))).status,403);
  assert.equal((await handler(pause({confirm:"yes"}))).status,400);
  assert.equal((await handler(pause({confirm:"PAUSE ADMISSION",admin:randomUUID()}))).status,400);
  assert.deepEqual(calls,[]);
  assert.deepEqual(await (await handler(pause())).json(),{status:"admission_closed"});
  assert.deepEqual(calls,[["pause",subject]]);
});
test("limiter or verifier failure cannot reach admin database",async()=>{
  for(const [overrides,code] of [[{limiter:async()=>false},429],
    [{verifyAdmin:async()=>{throw Error("provider down");}},503]]) {
    const {handler,calls}=fixture(overrides);
    assert.equal((await handler(pause())).status,code);assert.deepEqual(calls,[]);
  }
});
test("no resume, shell, reset or identity endpoints",async()=>{
  const {handler,calls}=fixture();
  for(const op of ["resume","shell","factory-reset","identity","spend"]) {
    const req=new Request(origin+"/api/v1/admin/"+op,{method:"POST",headers:{Authorization:"Bearer synthetic"}});
    assert.equal((await handler(req)).status,404);
  }
  assert.deepEqual(calls,[]);
});
test("admin repository parameterizes and normalizes counts",async()=>{
  const calls=[];
  const repo=createAdminRepository(async(s,a)=>{calls.push([s,a]);return s.includes("status")?
    [{admission_open:false,pending:"0",processing:"1"}]:[{ok:true}];});
  assert.deepEqual(await repo.status(subject),{admission_open:false,pending:0,processing:1});
  assert.equal(await repo.pause(subject),true);
  assert.deepEqual(calls.map(x=>x[1]),[[subject],[subject]]);
});
