import test from "node:test";
import assert from "node:assert/strict";
import read from "../../netlify/workshop-functions/workshop-read.mjs";
import write from "../../netlify/workshop-functions/workshop-write.mjs";
const id="a".repeat(24),host=id+"--projectpenny.netlify.app";
const ctx={site:{id:"28c495fc-f47a-427b-9ee2-95d4eadd2d8d"},deploy:{id}};
test("draft routes return fixed smoke marker only",async()=>{
  for(const [handler,path,method,operation] of [
    [read,"/api/v1/workshop","GET","read"],
    [write,"/api/v1/bridge/workshop","POST","write"]]){
    const r=await handler(new Request("https://"+host+path,{method}),ctx);
    assert.equal(r.status,503);
    assert.deepEqual(await r.json(),{schema:"penny-workshop-smoke-v1",status:"unavailable",operation});
    assert.match(r.headers.get("cache-control"),/no-store/);
  }
});
test("wrong site, host, method or direct function path denied",async()=>{
  for(const [url,context,method] of [
    ["https://"+host+"/api/v1/workshop",{...ctx,site:{id:"other"}},"GET"],
    ["https://other.netlify.app/api/v1/workshop",ctx,"GET"],
    ["https://"+host+"/api/v1/workshop",ctx,"POST"],
    ["https://"+host+"/.netlify/functions/workshop-read",ctx,"GET"]]){
    assert.equal((await read(new Request(url,{method}),context)).status,404);
  }
});
