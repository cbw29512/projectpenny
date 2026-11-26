import test from "node:test";
import assert from "node:assert/strict";
import {createAdminRuntime} from "../../netlify/runtime/admin.mjs";
import {loadAdminRuntime} from "../../netlify/runtime/admin-config.mjs";

const id="12345678-1234-4234-8234-123456789abc";
const env=()=>({CONTEXT:"production",PENNY_ADMIN_ENABLED:"true",
  PENNY_ORIGIN:"https://penny.example",PENNY_ADMIN_DB_ROLE:"admin_scope",
  PENNY_MEMBER_DB_ROLE:"member_scope",PENNY_BRIDGE_DB_ROLE:"bridge_scope",
  PENNY_ADMIN_DB_URL:"postgresql://admin_scope:fixture@db.example/penny"});
const req=()=>new Request("https://penny.example/api/v1/admin/status",
  {headers:{authorization:"Bearer fixture"}});
const verifyAdmin=async()=>({scope:"admin",subject:id,mfaAt:990,expiresAt:1100});
function fixture(unsafe=false) {
  const calls=[];
  class Pool {
    constructor(options){calls.push(options);}
    on(){}
    async connect(){return {release:()=>{},query:async(sql,args)=>{
      calls.push({sql,args});
      if(sql.includes("current_user")) return {rows:[{role:"admin_scope",login:"admin_scope",unsafe}]};
      if(sql.includes("mailbox_admin_allow")) return {rows:[{ok:true}]};
      return {rows:[{admission_open:false,pending:"2",processing:"1"}]};
    }};}
  }
  return {Pool,calls};
}
test("admin configuration rejects shared roles and TLS overrides",()=>{
  assert.equal(loadAdminRuntime({...env(),CONTEXT:"deploy-preview"}),null);
  assert.throws(()=>loadAdminRuntime({...env(),PENNY_ADMIN_DB_ROLE:"member_scope"}));
  assert.throws(()=>loadAdminRuntime({...env(),PENNY_ADMIN_DB_URL:env().PENNY_ADMIN_DB_URL+"?sslmode=disable"}));
});
test("missing verifier fails closed without constructing pool",async()=>{
  const {Pool,calls}=fixture();
  const handler=createAdminRuntime({env:env(),Pool});
  assert.equal((await handler(req())).status,503);
  assert.equal(calls.length,0);
});
test("verified admin uses dedicated TLS pool and persistent limiter",async()=>{
  const {Pool,calls}=fixture();
  const config=env();
  const handler=createAdminRuntime({env:config,Pool,verifyAdmin,now:()=>1000});
  const response=await handler(req());
  assert.equal(response.status,200);
  assert.deepEqual(await response.json(),{admissionOpen:false,pending:2,processing:1});
  assert.equal(calls[0].ssl.rejectUnauthorized,true);
  assert.equal(calls[0].connectionString,config.PENNY_ADMIN_DB_URL);
  assert.match(calls[2].sql,/mailbox_admin_allow/);
  assert.deepEqual(calls[2].args,[id,"status"]);
  config.PENNY_ADMIN_ENABLED="false";
  assert.equal((await handler(req())).status,503);
  assert.equal(calls.length,5);
});
test("unsafe principal blocks all admin routines",async()=>{
  const {Pool,calls}=fixture(true);
  const handler=createAdminRuntime({env:env(),Pool,verifyAdmin,now:()=>1000});
  assert.equal((await handler(req())).status,503);
  assert.equal(calls.length,2);
});
test("stale MFA cannot reach database",async()=>{
  const {Pool,calls}=fixture();
  const handler=createAdminRuntime({env:env(),Pool,now:()=>1000,
    verifyAdmin:async()=>({scope:"admin",subject:id,mfaAt:1,expiresAt:1100})});
  assert.equal((await handler(req())).status,401);
  assert.equal(calls.length,1);
});
