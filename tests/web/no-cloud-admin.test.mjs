import test from "node:test";
import assert from "node:assert/strict";
import {existsSync,readFileSync} from "node:fs";
import {createGateway} from "../../netlify/gateway/handler.mjs";
import {createActivityHandler} from "../../netlify/projection/handler.mjs";
const origin="https://penny.example";
test("no cloud Maker UI or admin entrypoints",()=>{
 const root=path=>new URL("../../"+path,import.meta.url);
 for(const path of ["website/admin","private-maker","netlify/admin","netlify/runtime/admin.mjs",
                    "netlify/runtime/admin-config.mjs"])
   assert.equal(existsSync(root(path)),false,path);
 assert.match(readFileSync(root("netlify.toml"),"utf8"),/publish = "website"/);
 assert.doesNotMatch(readFileSync(root("website/index.html"),"utf8"),/href="\/?admin(?:\/|")/);
});
test("public gateways have no administrative routes",async()=>{
 const forbidden=()=>{throw Error("unexpected admin dependency call");};
 const repository=Object.fromEntries(["submit","read","claim","ack","answer","reject"]
    .map(op=>[op,forbidden]));
 const chat=createGateway({enabled:true,origin,verify:forbidden,limiter:forbidden,repository});
 const activity=createActivityHandler({enabled:true,origin,verify:forbidden,allow:forbidden,
    repository:{publish:forbidden,read:forbidden}});
 for(const handler of [chat,activity]){
   assert.equal((await handler(new Request(origin+"/api/v1/admin/status"))).status,404);
   assert.equal((await handler(new Request(origin+"/api/v1/admin/pause-admission",{method:"POST"}))).status,404);
 }
});
