import test from "node:test";
import assert from "node:assert/strict";
import {createHmac,randomUUID} from "node:crypto";
import {createVerifier} from "../../netlify/gateway/auth.mjs";
import {createGateway} from "../../netlify/gateway/handler.mjs";
import {createRepository} from "../../netlify/gateway/repository.mjs";

const origin="https://penny.example";
const memberKey=Buffer.alloc(32,1),bridgeKey=Buffer.alloc(32,2);
const now=1000,owner=randomUUID(),id=randomUUID(),key=randomUUID();
function token(scope="member",patch={},signKey) {
  const claims={aud:scope,sub:scope==="member"?owner:"nucbox-bridge",iat:now,exp:now+300,...patch};
  const payload=Buffer.from(JSON.stringify(claims)).toString("base64url");
  const mac=createHmac("sha256",signKey??(scope==="member"?memberKey:bridgeKey))
    .update("penny-beta-v1."+payload).digest("base64url");
  return "Bearer v1."+payload+"."+mac;
}
function fixture(overrides={}) {
  const calls=[];
  const repository=Object.fromEntries(["submit","read","claim","ack","answer","reject"].map(op=>
    [op,async(...args)=>{calls.push([op,...args]);return op==="submit"?
      {status:"accepted",question_id:id,replayed:false,private:"secret"}:
      op==="read"||op==="claim"?null:{ok:true};}]));
  const handler=createGateway({verify:createVerifier({memberKey,bridgeKey,now:()=>now}),
    limiter:async()=>true,repository,origin,enabled:true,...overrides});
  return {handler,calls};
}
function req(path="/api/v1/questions",body={key,text:"Hi"},auth=token(),extra={}) {
  const headers={Authorization:auth,"Content-Type":"application/json",...extra.headers};
  return new Request(origin+path,{method:"POST",body:JSON.stringify(body),...extra,headers});
}
test("gateway defaults closed",async()=>{
  const {handler,calls}=fixture({enabled:undefined});
  assert.equal((await handler(req())).status,503); assert.deepEqual(calls,[]);
});
test("verified owner controls admission and only allowed fields are returned",async()=>{
  const {handler,calls}=fixture();
  const res=await handler(req());
  assert.equal(res.status,202);
  assert.deepEqual(await res.json(),{status:"accepted",id,replayed:false});
  assert.deepEqual(calls,[["submit",owner,{key,text:"Hi"}]]);
  assert.equal(res.headers.get("cache-control"),"private, no-store");
});
test("reject forged, expired, excessive lifetime, and cross-scope credentials",async()=>{
  const {handler,calls}=fixture();
  for(const auth of [token("member",{},bridgeKey),token("member",{exp:now}),
    token("member",{exp:now+901}),token("bridge"),"Bearer broken"])
    assert.equal((await handler(req(undefined,undefined,auth))).status,401);
  assert.equal((await handler(req("/api/v1/bridge/claim",{},token()))).status,401);
  assert.deepEqual(calls,[]);
});
test("reject unknown owner fields and cross-origin requests",async()=>{
  const {handler,calls}=fixture();
  assert.equal((await handler(req(undefined,{key,text:"Hi",owner:randomUUID()}))).status,400);
  assert.equal((await handler(req(undefined,undefined,undefined,{headers:{Origin:"https://evil.example"}}))).status,403);
  assert.deepEqual(calls,[]);
});
test("mandatory throttle precedes storage",async()=>{
  const {handler,calls}=fixture({limiter:async()=>false});
  const res=await handler(req());assert.equal(res.status,429);
  assert.equal(res.headers.get("retry-after"),"60");assert.deepEqual(calls,[]);
});
test("limiter failure closes admission",async()=>{
  const {handler,calls}=fixture({limiter:async()=>{throw Error("failure");}});
  assert.equal((await handler(req())).status,503);assert.deepEqual(calls,[]);
});
test("bound request bytes, content encoding, question size",async()=>{
  const {handler,calls}=fixture();
  assert.equal((await handler(req(undefined,{key,text:"x".repeat(10001)}))).status,413);
  assert.equal((await handler(req(undefined,{key,text:"x".repeat(2001)}))).status,400);
  assert.equal((await handler(req(undefined,undefined,undefined,{headers:{"Content-Encoding":"gzip"}}))).status,415);
  assert.deepEqual(calls,[]);
});
test("read uses authenticated owner; foreign or absent row is not found",async()=>{
  const {handler,calls}=fixture();
  const res=await handler(new Request(origin+"/api/v1/questions/"+id,{headers:{Authorization:token()}}));
  assert.equal(res.status,404);assert.deepEqual(calls,[["read",owner,id]]);
});
test("bridge scope supports narrow claim and fenced answer",async()=>{
  const {handler,calls}=fixture();
  assert.equal((await handler(req("/api/v1/bridge/claim",{},token("bridge")))).status,200);
  const body={id,fence:randomUUID(),text:"Reply"};
  assert.equal((await handler(req("/api/v1/bridge/answer",body,token("bridge")))).status,200);
  assert.deepEqual(calls,[["claim"],["answer",body]]);
});
test("no generic tool, SQL, administration or URL routing",async()=>{
  const {handler,calls}=fixture();
  for(const path of ["/api/v1/bridge/sql","/api/v1/admin","/api/v1/bridge/constructor"])
    assert.equal((await handler(req(path,{},token("bridge")))).status,404);
  assert.deepEqual(calls,[]);
});
test("repository uses separated adapters and SQL parameters",async()=>{
  const calls=[];
  const repo=createRepository({memberQuery:async(s,a)=>{calls.push(["member",s,a]);return [];},
    bridgeQuery:async(s,a)=>{calls.push(["bridge",s,a]);return [];}});
  const text="' OR 1=1 --";
  await repo.submit(owner,{key,text});await repo.claim();
  assert.equal(calls[0][0],"member");assert.ok(!calls[0][1].includes(text));
  assert.deepEqual(calls[0][2],[owner,key,text]);assert.equal(calls[1][0],"bridge");
});
test("same signing key cannot be used across scopes",()=>{
  assert.throws(()=>createVerifier({memberKey,bridgeKey:memberKey}));
});
