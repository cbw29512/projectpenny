import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createMakerClient} from "../../private-maker/client.mjs";
import {createAdminGateway} from "../../netlify/admin/handler.mjs";
const origin="https://penny.example",id="12345678-1234-4234-8234-123456789abc";
function fixture(){
 let now=1000000,open=true,lose=true,mfaAt=999;const calls=[];
 const gateway=createAdminGateway({enabled:true,origin,now:()=>Math.floor(now/1000),
   verifyAdmin:async bearer=>bearer==="Bearer fixture"?{scope:"admin",subject:id,mfaAt,expiresAt:Math.floor(now/1000)+120}:null,
   limiter:async()=>true,repository:{status:async()=>({admission_open:open,pending:2,processing:1}),
     pause:async()=>{open=false;return true;}}});
 const client=createMakerClient({enabled:true,clock:()=>now,fetcher:async(path,opts)=>{
   calls.push(path);
   const response=await gateway(new Request(origin+path,{...opts,headers:{...opts.headers,...(opts.method==="POST"?{Origin:origin}:{})}}));
   if(opts.method==="POST"&&lose){lose=false;throw Error("lost response");}return response;
 }});
 return {client,calls,advance:ms=>{now+=ms;},oldMfa:()=>{mfaAt=100;}};
}
test("confirmed read, exact pause confirmation, lost response and status reconciliation",async()=>{
 const f=fixture(),c=f.client;
 assert.throws(()=>createMakerClient());assert.equal(c.signIn("fixture"),true);
 assert.equal(f.calls.length,0);assert.equal(c.snapshot().canPause,false);
 await c.read();assert.deepEqual(c.snapshot().status,{admissionOpen:true,pending:2,processing:1});
 f.advance(5000);await c.pause("wrong");assert.equal(f.calls.length,1);
 await c.pause("PAUSE ADMISSION");assert.equal(c.snapshot().uncertain,true);
 assert.equal(c.snapshot().status,null);assert.equal(c.snapshot().canPause,false);
 f.advance(5000);await c.read();assert.equal(c.snapshot().status.admissionOpen,false);
 assert.equal(c.snapshot().uncertain,false);assert.equal(c.snapshot().canPause,false);
 f.advance(60000);assert.equal(c.snapshot().status,null);
 c.signOut();assert.equal(c.snapshot().signedIn,false);
});
test("stale MFA cannot confirm a pause",async()=>{
 const f=fixture(),c=f.client;c.signIn("fixture");await c.read();
 f.advance(5000);f.oldMfa();await c.pause("PAUSE ADMISSION");
 assert.equal(c.snapshot().status,null);assert.equal(c.snapshot().uncertain,true);
});
test("private console is excluded from public deploy",()=>{
 const root=p=>readFileSync(new URL("../../"+p,import.meta.url),"utf8");
 assert.match(root("netlify.toml"),/publish = "website"/);
 assert.doesNotMatch(root("website/index.html"),/private-maker/);
 assert.match(root("private-maker/index.html"),/id="maker-pause" type="button" disabled/);
});
