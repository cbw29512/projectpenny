import test from "node:test";
import assert from "node:assert/strict";
import {createHmac,randomUUID} from "node:crypto";
import {loadRuntime} from "../../netlify/runtime/config.mjs";
import {createScopedQuery} from "../../netlify/runtime/scoped-query.mjs";
import {createRuntimeHandler} from "../../netlify/runtime/gateway.mjs";

const origin="https://penny.example",id=randomUUID(),key="ab".repeat(32);
const env={CONTEXT:"production",PENNY_GATEWAY_ENABLED:"true",PENNY_ORIGIN:origin,
  PENNY_MEMBER_DB_ROLE:"penny_member",PENNY_BRIDGE_DB_ROLE:"penny_bridge",
  PENNY_MEMBER_DB_URL:"postgres://penny_member:synthetic@db.example/penny",
  PENNY_BRIDGE_DB_URL:"postgres://penny_bridge:synthetic@db.example/penny",
  PENNY_MEMBER_KEY_HEX:key,PENNY_BRIDGE_KEY_HEX:"cd".repeat(32)};
function request(){
  const t=Math.floor(Date.now()/1000);
  const payload=Buffer.from(JSON.stringify({aud:"member",sub:id,iat:t,exp:t+300})).toString("base64url");
  const sig=createHmac("sha256",Buffer.from(key,"hex")).update("penny-beta-v1."+payload).digest("base64url");
  return new Request(origin+"/api/v1/questions",{method:"POST",
    headers:{Authorization:"Bearer v1."+payload+"."+sig,"Content-Type":"application/json"},
    body:JSON.stringify({key:randomUUID(),text:"Hello"})});
}
test("closed by default and outside production without opening a pool",async()=>{
  for(const e of [{},{...env,CONTEXT:"deploy-preview"},{...env,PENNY_GATEWAY_ENABLED:"false"}]) {
    const handler=createRuntimeHandler({env:e,Pool:class{constructor(){throw Error("must not connect");}}});
    assert.equal((await handler(request())).status,503);
  }
});
test("configuration refuses ambient owner URL, shared role and TLS overrides",()=>{
  for(const e of [{...env,PENNY_MEMBER_DB_URL:undefined,NETLIFY_DB_URL:env.PENNY_BRIDGE_DB_URL},
    {...env,PENNY_BRIDGE_DB_ROLE:"penny_member"},
    {...env,PENNY_MEMBER_DB_URL:env.PENNY_MEMBER_DB_URL+"?sslmode=disable"},
    {...env,PENNY_MEMBER_DB_URL:env.PENNY_BRIDGE_DB_URL},
    {...env,PENNY_BRIDGE_KEY_HEX:key}]) assert.throws(()=>loadRuntime(e));
});
test("actual database principal checked before operation",async()=>{
  for(const row of [{role:"owner",login:"owner",unsafe:false},
    {role:"penny_member",login:"owner",unsafe:false},
    {role:"penny_member",login:"penny_member",unsafe:true}]) {
    let calls=0,released;
    const query=createScopedQuery({connect:async()=>({query:async()=>{calls++;return {rows:[row]};},
      release:v=>{released=v;}})},"penny_member");
    await assert.rejects(query("SELECT forbidden",[]));assert.equal(calls,1);assert.equal(released,true);
  }
});
test("candidate runtime composes auth, limiter and query on member pool",async()=>{
  const calls=[],pools=[];
  class Pool {
    constructor(options){this.options=options;pools.push(this);}
    on(){}
    async connect(){
      const role=new URL(this.options.connectionString).username;
      return {query:async(s,a)=>{
        calls.push({role,s,a});
        if(s.includes("current_user"))return {rows:[{role,login:role,unsafe:false}]};
        if(s.includes("allow_member"))return {rows:[{ok:true}]};
        if(s.includes("mailbox_submit"))return {rows:[{status:"accepted",question_id:id,replayed:false}]};
        throw Error("unexpected statement");
      },release(){}};
    }
  }
  const handler=createRuntimeHandler({env,Pool});
  const result=await handler(request());
  assert.equal(result.status,202);
  assert.deepEqual(await result.json(),{status:"accepted",id,replayed:false});
  assert.equal(pools.length,2);assert.ok(pools.every(p=>p.options.ssl.rejectUnauthorized));
  assert.equal(calls.length,4);assert.ok(calls.every(c=>c.role==="penny_member"));
  assert.equal(calls[1].a[0],id);
});

test("warm gateway rechecks pause and rejects configuration drift",async()=>{
  let calls=0;
  class Pool {
    on(){}
    constructor(){calls++;}
    async connect(){return {release(){},query:async(s)=>{
      calls++;
      if(s.includes("current_user"))return {rows:[{role:"penny_member",login:"penny_member",unsafe:false}]};
      if(s.includes("allow_member"))return {rows:[{ok:true}]};
      return {rows:[{status:"accepted",question_id:id,replayed:false}]};
    }};}
  }
  const config={...env};
  const handler=createRuntimeHandler({env:config,Pool});
  assert.equal((await handler(request())).status,202);
  const before=calls;
  config.PENNY_GATEWAY_ENABLED="false";
  assert.equal((await handler(request())).status,503);
  config.PENNY_GATEWAY_ENABLED="true";
  config.PENNY_MEMBER_KEY_HEX="ef".repeat(32);
  assert.equal((await handler(request())).status,503);
  config.PENNY_MEMBER_KEY_HEX=key;
  config.CONTEXT="deploy-preview";
  assert.equal((await handler(request())).status,503);
  assert.equal(calls,before);
});
