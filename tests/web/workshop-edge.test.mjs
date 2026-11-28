import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createWorkshopEntry} from "../../netlify/runtime/workshop-entry.mjs";
import read,{config as readConfig} from "../../netlify/workshop-functions/workshop-read.mjs";
import write,{config as writeConfig} from "../../netlify/workshop-functions/workshop-write.mjs";
const origin="https://projectpenny.netlify.app";
const ctx={site:{id:"28c495fc-f47a-427b-9ee2-95d4eadd2d8d"},
  deploy:{context:"production",published:true,id:"reviewed-fixture"}};
const env={PENNY_ORIGIN:origin,PENNY_WORKSHOP_ENABLED:"true",
  PENNY_WORKSHOP_REVIEWED_DEPLOY_ID:"reviewed-fixture"};
const req=()=>new Request(origin+"/api/v1/workshop");
test("literal provider rate limits use two supported Pro rules; not selected for default deployment",()=>{
  assert.deepEqual(readConfig,{path:"/api/v1/workshop",method:["GET"],
    rateLimit:{windowLimit:6,windowSize:60,aggregateBy:["ip","domain"]}});
  assert.deepEqual(writeConfig,{path:"/api/v1/bridge/workshop",method:["POST"],
    rateLimit:{windowLimit:3,windowSize:60,aggregateBy:["ip","domain"]}});
  assert.doesNotMatch(readFileSync("netlify.toml","utf8"),/workshop-functions/);
});
test("smoke entries always return unavailable without opening a database",async()=>{
  assert.equal((await read(req(),ctx)).status,503);
  assert.equal((await write(new Request(origin+"/api/v1/bridge/workshop",{method:"POST"}),ctx)).status,503);
});
test("only exact published reviewed production context may reach injected runtime",async()=>{
  let loaded=0,calls=0;
  const handler=createWorkshopEntry({operation:"read",env,loadRuntime:async(e)=>{
    loaded++;assert.equal(e.CONTEXT,"production");
    return async()=>{calls++;return new Response("fixture");};
  }});
  for(const bad of [undefined,{...ctx,site:{id:"other"}},
    {...ctx,deploy:{...ctx.deploy,published:false}},
    {...ctx,deploy:{...ctx.deploy,context:"deploy-preview"}},
    {...ctx,deploy:{...ctx.deploy,id:"new-deploy"}}]){
    assert.equal((await handler(req(),bad)).status,503);
  }
  assert.equal((await handler(new Request(origin+"/api/v1/workshop?x=1"),ctx)).status,404);
  assert.equal((await handler(new Request(origin+"/api/v1/workshop",{method:"POST"}),ctx)).status,404);
  assert.equal(loaded,0);
  assert.equal((await handler(req(),ctx)).status,200);
  assert.equal((await handler(req(),ctx)).status,200);
  assert.equal(loaded,1);assert.equal(calls,2);
  env.PENNY_WORKSHOP_ENABLED="false";
  assert.equal((await handler(req(),ctx)).status,503);
  env.PENNY_WORKSHOP_ENABLED="true";
});
