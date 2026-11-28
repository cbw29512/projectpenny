import test from "node:test";
import assert from "node:assert/strict";
import {randomUUID} from "node:crypto";
import {createCommunityHandler} from "../../netlify/community/handler.mjs";
import {createCommunityRepository} from "../../netlify/community/repository.mjs";
const origin="https://penny.example", owner=randomUUID(), id=randomUUID(), key=randomUUID(), fence=randomUUID();
const now=1800000000;
function fixture(overrides={}) {
  const calls=[];
  const repository={
    submit:async(...a)=>{calls.push(["submit",...a]);return {status:"accepted",suggestion_id:id,replayed:false,secret:"private"};},
    claim:async()=>{calls.push(["claim"]);return {suggestion_id:id,owner_id:owner,request_key:key,fence,body:"Useful idea",expires_at:new Date((now+600)*1000),lease_until:new Date((now+300)*1000),secret:"private"};},
    ack:async b=>{calls.push(["ack",b]);return {ok:true};}
  };
  const handler=createCommunityHandler({origin,repository,enabled:true,now:()=>now,
    verify:(auth,scope)=>auth===scope?{scope,subject:scope==="member"?owner:"nucbox-bridge"}:null,
    limiter:async()=>true,...overrides});
  return {handler,calls};
}
const request=(path,body,auth="member")=>new Request(origin+path,{method:"POST",
  headers:{Authorization:auth,"Content-Type":"application/json"},body:JSON.stringify(body)});
test("community admission stays default closed and derives owner from identity",async()=>{
  const off=fixture({enabled:undefined});
  assert.equal((await off.handler(request("/api/v1/suggestions",{key,text:"Useful idea"}))).status,503);
  assert.deepEqual(off.calls,[]);
  const {handler,calls}=fixture();
  const r=await handler(request("/api/v1/suggestions",{key,text:"Useful idea"}));
  assert.equal(r.status,202);
  assert.deepEqual(await r.json(),{status:"accepted",id,replayed:false});
  assert.deepEqual(calls,[["submit",owner,{key,text:"Useful idea"}]]);
});
test("community bridge claim and ack are scope-bound and exact",async()=>{
  const {handler,calls}=fixture();
  const path="/api/v1/bridge/community/";
  assert.equal((await handler(request(path+"claim",{}))).status,401);
  const r=await handler(request(path+"claim",{},"bridge"));
  assert.deepEqual(await r.json(),{id,owner,key,fence,text:"Useful idea",expiresAt:now+600,leaseUntil:now+300});
  assert.equal((await handler(request(path+"ack",{id,fence,role:"admin"},"bridge"))).status,400);
  assert.equal((await handler(request(path+"ack",{id,fence},"bridge"))).status,200);
  assert.deepEqual(calls,[["claim"],["ack",{id,fence}]]);
});
test("shared throttle and ASCII parity fail closed before storage",async()=>{
  const f=fixture({limiter:async()=>false});
  assert.equal((await f.handler(request("/api/v1/suggestions",{key,text:"Useful idea"}))).status,429);
  assert.deepEqual(f.calls,[]);
  const g=fixture();
  for(const b of [{key,text:"Café idea"},{key,text:"Useful idea",owner}])
    assert.equal((await g.handler(request("/api/v1/suggestions",b))).status,400);
  assert.deepEqual(g.calls,[]);
});
test("community queries use separate fixed role adapters",async()=>{
  const calls=[];
  const repo=createCommunityRepository({memberQuery:async(s,a)=>{calls.push(["member",s,a]);return [];},
    bridgeQuery:async(s,a)=>{calls.push(["bridge",s,a]);return [];}});
  await repo.submit(owner,{key,text:"Useful idea"});await repo.claim();await repo.ack({id,fence});
  assert.deepEqual(calls.map(c=>c[0]),["member","bridge","bridge"]);
  assert.deepEqual(calls[0][2],[owner,key,"Useful idea"]);
  assert.deepEqual(calls[2][2],[id,fence]);
});
