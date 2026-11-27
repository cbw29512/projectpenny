import test from "node:test";
import assert from "node:assert/strict";
import {createHmac,randomUUID} from "node:crypto";
import {createVerifier} from "../../netlify/gateway/auth.mjs";
import {createGateway} from "../../netlify/gateway/handler.mjs";
import {createBetaMailbox} from "../../website/assets/beta-mailbox.mjs";

const origin="https://penny.example",owner=randomUUID(),id=randomUUID(),key=randomUUID();
const memberKey=Buffer.alloc(32,1),bridgeKey=Buffer.alloc(32,2);
const claims=Buffer.from(JSON.stringify({aud:"member",sub:owner,iat:1000,exp:1300})).toString("base64url");
const token="v1."+claims+"."+createHmac("sha256",memberKey).update("penny-beta-v1."+claims).digest("base64url");
function fixture(){
  let now=0,lose=true;const calls=[];
  const repository={submit:async(who,body)=>{
    calls.push([who,body]);return {status:"accepted",question_id:id,replayed:calls.length>1};
  },read:async(who,q)=>{assert.equal(who,owner);assert.equal(q,id);
    return {question_id:id,status:"answered",reply:"A reviewed answer."};},
    claim:async()=>null,ack:async()=>({ok:true}),answer:async()=>({ok:true}),reject:async()=>({ok:true})};
  const handler=createGateway({verify:createVerifier({memberKey,bridgeKey,now:()=>1001}),
    limiter:async()=>true,repository,origin,enabled:true});
  const client=createBetaMailbox({enabled:true,uuid:()=>key,clock:()=>now,
    fetcher:async(path,options)=>{
      assert.ok(path.startsWith("/api/v1/questions"));assert.equal(options.redirect,"error");
      const res=await handler(new Request(origin+path,options));
      if(lose){lose=false;throw Error("synthetic response loss");}
      return res;
    }});
  return {client,calls,advance:()=>{now+=15000;}};
}
test("closed by default and exact replay after lost acceptance",async()=>{
  assert.throws(()=>createBetaMailbox());
  const {client,calls,advance}=fixture();
  assert.equal(client.signIn(token),true);
  assert.equal((await client.submit("Hello")).status,"uncertain");
  assert.equal((await client.submit("Changed")).status,"uncertain");
  assert.equal((await client.submit("Hello")).status,"uncertain");
  assert.equal(calls.length,1);
  advance();assert.equal((await client.submit("Hello")).id,id);
  assert.deepEqual(calls,[[owner,{key,text:"Hello"}],[owner,{key,text:"Hello"}]]);
  advance();assert.equal((await client.read()).text,"A reviewed answer.");
  assert.equal(client.next(),true);
  client.signOut();assert.deepEqual(client.snapshot(),{signedIn:false,busy:false,hasDraft:false,id:null,status:"idle",text:null});
});
test("reject mismatched answer IDs and no unsolicited requests",async()=>{
  let calls=0,now=0;
  const c=createBetaMailbox({enabled:true,uuid:()=>key,clock:()=>now,fetcher:async()=>{
    calls++;return new Response(JSON.stringify(calls===1?{status:"accepted",id,replayed:false}:
      {id:randomUUID(),status:"answered",text:"Foreign answer"}),{status:calls===1?202:200,
      headers:{"Content-Type":"application/json"}});
  }});
  assert.equal(c.signIn(token),true);assert.equal(calls,0);
  await c.submit("Hi");now=15000;
  assert.equal((await c.read()).status,"unavailable");assert.equal(c.snapshot().text,null);
  assert.equal(c.next(),false);
});
